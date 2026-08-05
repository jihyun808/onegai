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
from app.services.kysing import USER_AGENT, _parse as parse_kysing_rows
from app.utils import db

logger = logging.getLogger(__name__)

MANANA_RELEASE = "https://api.manana.kr/karaoke/release/{ym}/{brand}.json"
KYSING_LATEST = "https://kysing.kr/latest/"

# manana에 데이터가 있는 가장 이른 달 (그 이전은 전부 0건이다)
EARLIEST = date(2000, 1, 1)

# 남의 서버다. 동시 요청 수를 낮추고 요청 사이에 간격을 둔다.
# 급할 이유가 없다 — 백필은 한 번만 돌리고, 이후에는 하루 몇 건이다.
BACKFILL_WORKERS = 2
REQUEST_DELAY = 0.4

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
