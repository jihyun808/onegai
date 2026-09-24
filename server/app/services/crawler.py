"""카탈로그 크롤러.

전략은 두 가지다.

1. **월별 백필** — manana `/karaoke/release/{YYYYMM}/{brand}.json`
   한 번 호출에 그 달 신곡이 통째로 온다. 브랜드당 ~320개월이면 전량이다.
   가장 싸고 안전한 열거 방법이라 과거 카탈로그는 전부 이걸로 채운다.

2. **금영 최신 보완** — kysing.kr `/latest/` (이달의 신곡)
   manana의 금영 데이터가 2026-04 이후 멈춰 있어 월별 백필로는 못 채운다.
   공식 신곡 페이지를 매일 훑어 누적한다.

크롤링이 실패해도 이미 쌓인 DB로 서비스는 계속된다. 그 점이 실시간 조회보다
나은 가장 큰 이유다.
"""

import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from html import unescape
from urllib.parse import urlencode

import requests
from flask import current_app

from app.models import song
from app.services import kysing
from app.services.kysing import USER_AGENT, _parse as parse_kysing_rows
from app.utils import db

logger = logging.getLogger(__name__)

MANANA_RELEASE = "https://api.manana.kr/karaoke/release/{ym}/{brand}.json"
KYSING_LATEST = "https://kysing.kr/latest/"
# 금영 '노래방 책' 일본곡 색인. 검색과 달리 **국가로 좁혀 전량 열거**할 수 있다.
KYSING_BOOK = "https://kysing.kr/karaoke-book/"

# manana에 데이터가 있는 가장 이른 달 (그 이전은 전부 0건이다)
EARLIEST = date(2000, 1, 1)

# 남의 서버다. 동시 요청 수를 낮추고 요청 사이에 간격을 둔다.
# 급할 이유가 없다 — 백필은 한 번만 돌리고, 이후에는 하루 몇 건이다.
BACKFILL_WORKERS = 2
REQUEST_DELAY = 0.4

# 색인 크롤은 **혼자, 아주 천천히** 돈다.
# 전량 열거라 남의 서버에 부담이 가장 큰 작업이라서,
# 동시 요청 없이 요청 사이에 넉넉한 간격을 둔다. 107문자 × 2~3페이지에
# 3초 간격이면 15분 안팎이고, 하루 한 번이면 초당 0.0003요청 꼴이다.
BOOK_REQUEST_DELAY = 3.0
# 한 색인 문자가 이보다 길면 무언가 잘못된 것이다 (페이지당 200행 기준).
BOOK_MAX_PAGES = 15

# 노래방에 아직 등록되지 않은 예정곡은 받지 않는다.
# 금영은 발매 예정월을 미리 올려두는데, 그 번호를 눌러도 기계에 곡이 없다.
_throttle = threading.Semaphore(1)
_last_request = [0.0]


def _wait_turn():
    """요청 사이에 최소 간격을 둔다."""
    with _throttle:
        gap = time.monotonic() - _last_request[0]
        if gap < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - gap)
        _last_request[0] = time.monotonic()


def _drop_unreleased(entries):
    """아직 발매되지 않은 곡을 걸러낸다."""
    today = date.today().isoformat()
    return [e for e in entries if not (e.get("release") or "") > today]

_PAGE_LINK = re.compile(r'href="\?s_page=(\d+)"')


def months(start=None, end=None):
    """백필 대상 월 목록을 'YYYYMM' 문자열로 만든다."""
    start = start or EARLIEST
    end = end or date.today()

    out = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        out.append(f"{year}{month:02d}")
        month += 1
        if month > 12:
            year, month = year + 1, 1
    return out


def _record(source, brand, scope, found, inserted, status="ok", message=""):
    db.execute_many(
        """
        INSERT INTO crawl_log (source, brand, scope, found, inserted, status, message)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            found = VALUES(found), inserted = VALUES(inserted),
            status = VALUES(status), message = VALUES(message),
            created_at = CURRENT_TIMESTAMP
        """,
        [(source, brand, scope, found, inserted, status, message[:255])],
    )


def _fetch_month(brand, ym):
    _wait_turn()
    url = MANANA_RELEASE.format(ym=ym, brand=brand)
    response = requests.get(url, timeout=current_app.config["MANANA_TIMEOUT"])
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, list) else []


def backfill_month(brand, ym):
    """한 달치를 가져와 저장한다. (찾은 수, 저장된 수)"""
    try:
        entries = _fetch_month(brand, ym)
    except Exception as exc:
        logger.warning("백필 실패 %s %s: %s", brand, ym, exc)
        _record("manana", brand, ym, 0, 0, "failed", str(exc))
        return 0, 0

    # 응답에 다른 브랜드가 섞여 올 수 있어 걸러낸다
    entries = _drop_unreleased([e for e in entries if e.get("brand") == brand])
    saved = song.upsert(entries, "manana")
    _record("manana", brand, ym, len(entries), saved)
    return len(entries), saved


def backfill(brands=("tj", "kumyoung"), start=None, end=None, skip_done=True):
    """월별 백필. 이미 성공한 달은 건너뛴다(재시작 가능)."""
    targets = months(start, end)
    app = current_app._get_current_object()

    done = set()
    if skip_done:
        rows = db.query(
            "SELECT brand, scope FROM crawl_log "
            "WHERE source = 'manana' AND status = 'ok'"
        )
        done = {(r["brand"], r["scope"]) for r in rows or []}

    jobs = [
        (brand, ym)
        for brand in brands
        for ym in targets
        if (brand, ym) not in done
    ]

    total_found = total_saved = 0

    def run(job):
        with app.app_context():
            return backfill_month(*job)

    with ThreadPoolExecutor(max_workers=BACKFILL_WORKERS) as pool:
        for found, saved in pool.map(run, jobs):
            total_found += found
            total_saved += saved

    logger.info("백필 완료: %d개월, %d곡 확인, %d곡 저장", len(jobs), total_found, total_saved)
    return {"months": len(jobs), "found": total_found, "saved": total_saved}


def _fetch_kysing_latest(page):
    _wait_turn()
    url = f"{KYSING_LATEST}?{urlencode({'s_page': page})}"
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=current_app.config["KYSING_TIMEOUT"],
    )
    response.raise_for_status()
    return response.text


def crawl_kysing_latest(max_pages=20):
    """금영 이달의 신곡. manana가 못 채우는 최신 금영곡을 여기서 얻는다."""
    collected = {}

    try:
        for page in range(1, max_pages + 1):
            html = _fetch_kysing_latest(page)
            rows = parse_kysing_rows(html)
            fresh = [r for r in rows if r["no"] not in collected]
            if not fresh:
                break
            for row in fresh:
                collected[row["no"]] = row
            # 다음 페이지 링크가 없으면 끝
            if not _PAGE_LINK.search(unescape(html)):
                break
    except Exception as exc:
        logger.warning("금영 신곡 크롤링 실패: %s", exc)
        _record("kysing", "kumyoung", "latest", len(collected), 0, "failed", str(exc))
        if not collected:
            return {"found": 0, "saved": 0}

    entries = _drop_unreleased(list(collected.values()))
    saved = song.upsert(entries, "kysing")
    _record("kysing", "kumyoung", "latest", len(entries), saved)
    logger.info("금영 신곡: %d곡 확인, %d곡 저장", len(entries), saved)
    return {"found": len(entries), "saved": saved}


# 색인 문자 107종. 라이브 페이지의 색인 목록에서 그대로 옮겼다.
# 히라가나 전수 + 其他(가나로 시작하지 않는 것) + A~Z + ETC(0).
KYSING_BOOK_INDEX = (
    "ぁ か が さ ざ た だ な は ば ぱ ま や ゃ ら わ ん "
    "い ぃ き ぎ し じ ち ぢ に ひ び ぴ み り "
    "う ぅ く ぐ す ず つ づ ぬ ふ ぶ ぷ む ゆ ゅ る っ "
    "え ぇ け げ せ ぜ て で ね へ べ ぺ め れ "
    "お ぉ こ ご そ ぞ と ど の ほ ぼ ぽ も よ ょ ろ を 其他 "
    "A B C D E F G H I J K L M N O P Q R S T U V W X Y Z"
).split() + ["0"]

# 색인 행: 곡번호 / 제목 / 가수. 제목과 가수는 **속성과 본문 두 군데**에 있다.
#
# 둘 다 읽어서 긴 쪽을 쓴다. 어느 하나도 믿을 수 없기 때문이다.
#   - 본문은 화면 폭에 맞춰 잘릴 수 있다 (`..`로 끝난다)
#   - 속성은 제목에 따옴표가 들어가면 거기서 끊긴다. 금영이 이스케이프를
#     안 해서 `title="* ~アスタリスク~ ("BLEACH"OP)"`가 `* ~アスタリスク~ (`로 읽힌다
_BOOK_ROW = re.compile(
    r'index_search_num">(\d+)</li>\s*'
    r'<li class="index_search_tit" title="(.*?)"[^>]*>(.*?)</li>\s*'
    r'<li class="index_search_sng" title="(.*?)"[^>]*>(.*?)</li>',
    re.S,
)
_TRUNCATED = re.compile(r"(\.{2,}|…)\s*$")


def _fetch_kysing_book(index_char, page):
    """색인 한 장. **여기서만 느린 간격을 쓴다.**"""
    time.sleep(BOOK_REQUEST_DELAY)
    url = f"{KYSING_BOOK}?" + urlencode(
        {"city": "jp", "s_cd": 2, "keyword": "", "s_page": page, "s_value": index_char}
    )
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=current_app.config["KYSING_TIMEOUT"],
    )
    response.raise_for_status()
    return response.text


def _fuller(attr, text):
    """속성과 본문 중 온전해 보이는 쪽. 둘 다 잘렸으면 긴 쪽."""
    attr = unescape(attr or "").strip()
    text = unescape(re.sub(r"<[^>]+>", "", text or "")).strip()

    if _TRUNCATED.search(text) and attr:
        return attr
    return text if len(text) >= len(attr) else attr


def parse_kysing_book(html):
    """색인 페이지를 manana 스키마로. 발매일은 색인에 없어 비운다."""
    rows = []

    for no, tit_attr, tit_text, sng_attr, sng_text in _BOOK_ROW.findall(html):
        title = _fuller(tit_attr, tit_text)
        singer = _fuller(sng_attr, sng_text)
        if not title:
            continue
        rows.append(
            {
                "brand": "kumyoung",
                "no": no,
                "title": title,
                "singer": singer,
                "composer": "",
                "lyricist": "",
                # 색인에는 출시월이 없다. 이미 있는 행은 upsert가 유지한다.
                "release": "",
            }
        )

    return rows


def _looks_truncated(row):
    """색인이 잘라서 준 행인지.

    금영은 표시폭(30자 남짓)에서 `..`로 자른다. 제목에 따옴표가 있으면
    잘린 자리가 `(`나 `"`로 끝나기도 한다.
    """
    for value in (row["title"], row["singer"]):
        if _TRUNCATED.search(value) or value.endswith(('("', "(", '"')):
            return True
    return False


def _drop_truncated(rows):
    """잘린 행은 버린다.

    **금영은 어디서도 온전한 제목을 주지 않는다.** 색인·검색·곡번호 상세를
    모두 확인했는데 전부 30자 남짓에서 `..`로 자른다 (2026-08-19 실측,
    예: 44418 `366LOVEダイアリー ("KING OF PRISM -Shiny..`).

    그래서 보정 요청을 보내 봐야 소용이 없다 — 남의 서버만 친다.
    잘린 제목을 저장하면 **다른 소스로 온전하게 들어와 있던 행을 덮어쓰고**,
    match_key가 어긋나 태진 번호와 한 카드로 묶이지 않는다.

    버려도 그 곡을 못 찾는 것은 아니다. 검색할 때 공식을 직접 조회하는
    경로가 그대로 남아 있다 (5번의 폴백 사슬).
    """
    kept = [r for r in rows if not _looks_truncated(r)]
    dropped = len(rows) - len(kept)

    if dropped:
        logger.info("제목이 잘린 %d행은 넣지 않습니다 (전체 %d행)", dropped, len(rows))

    return kept


def crawl_kysing_book(index_chars=None, max_pages=BOOK_MAX_PAGES):
    """금영 일본곡을 색인으로 전량 훑는다.

    **가수 이름을 몰라도 빠짐없이 가져온다는 것이 요점이다.** 기존
    fill_gap()은 '아는 가수'로만 검색해서, 모르는 가수의 곡은 영영 못 넣었다.

    금영 검색 페이지와 달리 여기는 `city=jp`로 일본곡만 좁혀 준다.
    (5번에 '금영은 국가 필터가 없다'고 적어 두었던 것은 틀렸다.)

    **정중함이 최우선이다.** 동시 요청 없이 한 장씩, 3초 간격으로 받는다.
    한 색인 문자가 실패하면 그 문자만 건너뛰고 계속한다 — 전체를 멈추면
    이미 받은 것도 못 쓴다.
    """
    chars = list(index_chars or KYSING_BOOK_INDEX)
    collected = {}
    failed = []

    for char in chars:
        for page in range(1, max_pages + 1):
            try:
                rows = parse_kysing_book(_fetch_kysing_book(char, page))
            except Exception as exc:
                logger.warning("금영 색인 %r %d페이지 실패: %s", char, page, exc)
                failed.append(char)
                break

            if not rows:
                break

            fresh = [r for r in rows if r["no"] not in collected]
            for row in fresh:
                collected[row["no"]] = row

            # 새 번호가 하나도 없으면 마지막 페이지를 넘긴 것이다
            if not fresh:
                break

    entries = _drop_truncated(list(collected.values()))
    saved = song.upsert(entries, "kysing-book") if entries else 0

    status = "failed" if failed and not entries else "ok"
    _record(
        "kysing-book", "kumyoung", "jp-index", len(entries), saved, status,
        f"실패한 색인: {','.join(failed)}" if failed else "",
    )
    logger.info(
        "금영 일본곡 색인: %d곡 확인, %d행 반영 (실패 %d문자)",
        len(entries), saved, len(failed),
    )
    return {"found": len(entries), "saved": saved, "failed": failed}


def japanese_artists(brand="tj", limit=None):
    """일본곡을 부르는 가수 목록. 공백을 메울 때 검색어로 쓴다.

    TJ 카탈로그가 더 크다(가수 16,019명 vs 금영 11,692명).

    **가수 이름만 보면 안 된다.** Ado, YOASOBI, Vaundy, Aimer처럼
    로마자 이름을 쓰는 일본 가수가 통째로 빠진다(1,129명 → 1,681명).
    곡 제목에 일본어가 있으면 그 가수도 대상에 넣는다.
    """
    sql = """
        SELECT DISTINCT singer FROM songs
        WHERE brand = %s AND singer <> ''
          AND (singer REGEXP '[ぁ-んァ-ヶ一-龥]'
               OR title REGEXP '[ぁ-んァ-ヶ一-龥]')
        ORDER BY singer
    """
    params = [brand]
    if limit:
        sql += " LIMIT %s"
        params.append(limit)

    rows = db.query(sql, tuple(params))
    return [r["singer"] for r in rows or []]


def fill_gap(brand="kumyoung", artists=None, limit=None, skip_done=True):
    """가수별로 공식 사이트를 훑어 카탈로그 공백을 메운다.

    금영 공식에는 전곡 목록이 없어서 월별 열거가 불가능하다.
    대신 가수 이름으로는 검색되므로, 아는 가수를 하나씩 물어본다.

    **느리다. 그래야 한다.** 남의 서버를 1,000번 넘게 두드리는 작업이라
    크롤러의 속도 제한(_wait_turn)을 그대로 따른다. 한 번에 끝낼 필요가
    없으므로 중단해도 이어서 할 수 있게 진행 상황을 남긴다.
    """
    from app.services import kysing, tjmedia

    module = {"kumyoung": kysing, "tj": tjmedia}[brand]
    names = artists if artists is not None else japanese_artists(limit=limit)

    done = set()
    if skip_done:
        rows = db.query(
            "SELECT scope FROM crawl_log WHERE source = %s AND brand = %s "
            "AND status = 'ok' AND scope LIKE 'artist:%%'",
            (module.__name__.rsplit(".", 1)[-1], brand),
        )
        done = {r["scope"][len("artist:") :] for r in rows or []}

    source = module.__name__.rsplit(".", 1)[-1]
    total_found = total_saved = 0
    todo = [n for n in names if n not in done]
    logger.info("공백 메우기 시작: %s, 가수 %d명", brand, len(todo))

    for index, name in enumerate(todo, 1):
        _wait_turn()
        try:
            rows = module.search(name, search_type="singer")
        except Exception as exc:
            logger.info("가수 조회 실패 (%s): %s", name, exc)
            _record(source, brand, f"artist:{name}"[:32], 0, 0, "failed", str(exc))
            continue

        entries = _drop_unreleased([r for r in rows if r.get("brand") == brand])
        saved = song.upsert(entries, source)
        _record(source, brand, f"artist:{name}"[:32], len(entries), saved)
        total_found += len(entries)
        total_saved += saved

        if index % 50 == 0:
            logger.info("  %d/%d명 · %d곡 확인", index, len(todo), total_found)

    logger.info("공백 메우기 완료: %d명, %d곡 확인, %d행 반영", len(todo), total_found, total_saved)
    return {"artists": len(todo), "found": total_found, "saved": total_saved}


def daily():
    """매일 돌릴 작업. 이번 달과 지난달만 다시 훑고 금영 신곡을 받는다."""
    today = date.today()
    previous = date(today.year - (today.month == 1), today.month - 1 or 12, 1)

    result = backfill(start=previous, end=today, skip_done=False)
    result["kysing_latest"] = crawl_kysing_latest()
    return result
