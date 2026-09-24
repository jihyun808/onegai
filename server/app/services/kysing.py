"""금영 공식 사이트(kysing.kr) 검색 스크래퍼.

manana의 금영 데이터가 2026-04 이후 갱신되지 않아 최신곡이 통째로 빠진다.
공식 사이트에는 그 곡들이 있으므로 여기서 직접 긁는다.
(가수별로 manana보다 9~62곡 더 나온다. DECISIONS.md 참고)

**공개 API가 아니라 HTML 파싱이다.** 사이트 구조가 바뀌면 조용히 0건을 반환하게
되므로, 반드시 manana 폴백과 헬스체크를 함께 둔다.

응답은 manana와 같은 스키마로 변환해서 돌려준다. 그래야 상위 계층이
어느 소스에서 왔는지 신경 쓰지 않아도 된다.

결과 행 구조 (search_chart_list):
    [1] 곡번호  [2] 곡명(+가사)  [3] 아티스트  [4] 작곡가  [5] 작사가  [6] 출시월
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode

import requests
from flask import current_app

from app.utils.normalize import normalize_text

logger = logging.getLogger(__name__)

BASE_URL = "https://kysing.kr/search/"

# 브라우저가 아니면 막힐 수 있어 일반적인 UA를 쓴다
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

# 사이트의 검색 카테고리.
# 가사(4)는 금영에만 있다 — TJ 공식에는 가사 검색이 없다.
# "no"는 곡번호 정확검색. 색인이 잘라서 준 행을 보정할 때 쓴다 (40번).
CATEGORY = {"song": 2, "singer": 7, "lyrics": 4, "no": 1}

# 한 페이지에 15건. 폭주를 막기 위해 상한을 둔다.
PAGE_SIZE = 15
MAX_PAGES = 20
# 한 번에 동시에 받을 페이지 수. 남의 서버라 과하게 늘리지 않는다.
PAGE_BATCH = 3

_ROW_BLOCK = re.compile(r'<ul class="search_chart_list clear">(.*?)</ul>', re.S)
_CELL = re.compile(r"<li[^>]*>(.*?)</li>", re.S)
_TAG = re.compile(r"<[^>]+>")

# 곡명 칸에는 가사 전문이 딸려 온다. '닫기' 뒤부터가 가사다.
_LYRICS_SPLIT = re.compile(r"\s*닫기\s*")

# 가사 팝업. 곡명 칸 안에 통째로 들어 있어서 따로 요청할 필요가 없다.
_LYRICS_CONT = re.compile(r'<div class="LyricsCont">(.*?)</div>', re.S)
_LYRICS_TIT = re.compile(r'<p class="LyricsTit">.*?</p>', re.S)
_BR = re.compile(r"<br\s*/?>", re.I)

# 가사는 대체로 세 줄이 한 묶음이다: 한글 발음 / 후리가나 / 일본어 원문.
# 다만 'La la la' 같은 도입부는 발음이 필요 없어 묶음이 통째로 어긋난다.
# 그래서 줄 수를 세지 않고 줄마다 무엇인지를 보고 짝을 짓는다.
_HANGUL = re.compile(r"[가-힣]")
# 후리가나는 루비 위치 정보가 빠진 채로 온다 (`きょ/う//かん/ぱい/`).
# 히라가나와 구분선만 남은 줄인데, **구분선이 반드시 하나는 있다**.
# 이 조건이 없으면 `ずっと ずっと ずっと` 같은 히라가나 가사가 통째로 버려진다.
_RUBY = re.compile(r"^(?=[^/]*/)[ぁ-ゖー/\s]*$")

# 가사를 찾을 때 가수 검색을 몇 페이지까지 훑을지. 곡이 많은 가수를 위한 여유다.
LYRICS_MAX_PAGES = 4

# 출시월은 '2025.11' 형태다. manana의 'YYYY-MM-DD'에 맞춘다.
_RELEASE = re.compile(r"^(\d{4})\.(\d{1,2})$")


class KysingError(Exception):
    """금영 공식 사이트 조회 실패."""


def _text(fragment):
    from html import unescape

    return " ".join(unescape(_TAG.sub(" ", fragment)).split())


def _normalize_release(value):
    match = _RELEASE.match(value.strip())
    if not match:
        return ""
    year, month = match.groups()
    return f"{year}-{int(month):02d}-01"


def _row_blocks(page_html):
    """결과 행들의 칸 목록. 첫 블록은 헤더라 건너뛰고, 칸이 모자란 행은 버린다."""
    blocks = []
    for block in _ROW_BLOCK.findall(page_html)[1:]:
        cells = _CELL.findall(block)
        if len(cells) >= 7:
            blocks.append(cells)
    return blocks


def _title_singer(cells):
    """곡명 칸은 "제목 아티스트 닫기 <가사...>" 꼴이다. 제목과 가수만 떼어낸다."""
    title = _LYRICS_SPLIT.split(_text(cells[2]))[0]
    singer = _text(cells[3])
    if singer and title.endswith(singer):
        title = title[: -len(singer)].strip()
    return title, singer


def _parse(page_html):
    """결과 행을 manana 스키마로 변환한다. 첫 블록은 헤더라 건너뛴다."""
    rows = []

    for cells in _row_blocks(page_html):
        no = _text(cells[1])
        if not no.isdigit():
            continue

        title, singer = _title_singer(cells)

        rows.append(
            {
                "brand": "kumyoung",
                "no": no,
                "title": title,
                "singer": singer,
                "composer": _text(cells[4]),
                "lyricist": _text(cells[5]),
                "release": _normalize_release(_text(cells[6])),
            }
        )

    return rows


def _parse_lyrics(title_cell):
    """곡명 칸에 딸려 온 가사 팝업을 [{ko, ja}, ...]로 바꾼다. 못 읽으면 None.

    한글이 있으면 발음, 히라가나와 구분선뿐이면 후리가나, 나머지는 원문으로
    본다. 발음 줄을 들고 있다가 다음 원문 줄과 짝지어 준다.

    줄 수로 세 줄씩 끊지 않는 이유 — `ミスター`처럼 'La la la' 도입부로
    시작하는 곡은 발음 줄이 없어서 그 뒤 가사가 통째로 한 칸씩 밀린다.
    """
    block = _LYRICS_CONT.search(title_cell)
    if not block:
        return None

    body = _LYRICS_TIT.sub("", block.group(1))

    lines = []
    pending = None

    for row in (_text(part) for part in _BR.split(body)):
        if not row or _RUBY.match(row):
            continue

        if _HANGUL.search(row):
            # 발음이 연달아 나오면 앞엣것은 짝을 못 찾은 것이다
            if pending is not None:
                lines.append({"ko": pending, "ja": ""})
            pending = row
        else:
            lines.append({"ko": pending or "", "ja": row})
            pending = None

    if pending is not None:
        lines.append({"ko": pending, "ja": ""})

    return lines or None


def _fetch(keyword, category, page):
    params = {"category": category, "keyword": keyword, "s_page": page}
    url = f"{BASE_URL}?{urlencode(params, encoding='utf-8')}"

    # 가사 검색은 금영 서버가 전문을 훑느라 훨씬 오래 걸린다
    # (실측: 곡명 2초 vs 가사 11초). 같은 타임아웃을 쓰면 항상 실패한다.
    timeout = (
        current_app.config["KYSING_LYRICS_TIMEOUT"]
        if category == CATEGORY["lyrics"]
        else current_app.config["KYSING_TIMEOUT"]
    )

    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
        response.raise_for_status()
    except requests.Timeout as exc:
        raise KysingError("금영 공식 사이트 응답 시간이 초과되었습니다.") from exc
    except requests.RequestException as exc:
        raise KysingError("금영 공식 사이트 호출에 실패했습니다.") from exc

    return response.text


def search(keyword, search_type="song"):
    """금영 공식 사이트에서 검색한다. manana와 같은 스키마의 리스트를 반환."""
    category = CATEGORY.get(search_type)
    if category is None:
        raise ValueError(f"지원하지 않는 검색 타입입니다: {search_type}")

    first = _parse(_fetch(keyword, category, 1))

    # 금영은 부하가 걸리면 결과 없는 페이지를 간헐적으로 돌려준다.
    # (같은 요청을 다시 보내면 정상 응답이 온다)
    # 첫 페이지가 비면 한 번 더 시도한다. 진짜 0건이면 그대로 0건이다.
    if not first:
        first = _parse(_fetch(keyword, category, 1))

    collected = {row["no"]: row for row in first}
    if len(first) < PAGE_SIZE:
        return list(collected.values())

    # 페이지당 2초가 넘어서 직렬로 돌면 금방 쌓인다.
    # 몇 페이지인지 미리 알 수 없으므로 몇 장씩 묶어 동시에 받는다.
    # 마지막 페이지를 넘기면 같은 내용이 반복되므로 새 번호가 없으면 멈춘다.
    app = current_app._get_current_object()

    def fetch_page(page):
        with app.app_context():
            try:
                return _parse(_fetch(keyword, category, page))
            except KysingError as exc:
                logger.info("금영 %d페이지 실패, 여기까지만 씁니다: %s", page, exc)
                return []

    # 대부분의 검색은 2페이지에서 끝난다. 처음부터 여러 장을 동시에 받으면
    # 쓰지도 않을 페이지를 부르면서 금영 서버만 느려진다.
    # 2페이지는 혼자 받고, 그래도 꽉 차 있으면 그때부터 묶어서 받는다.
    page, size = 2, 1
    while page <= MAX_PAGES:
        batch = list(range(page, min(page + size, MAX_PAGES + 1)))
        with ThreadPoolExecutor(max_workers=len(batch)) as pool:
            pages = list(pool.map(fetch_page, batch))

        fresh = 0
        for rows in pages:
            for row in rows:
                if row["no"] not in collected:
                    collected[row["no"]] = row
                    fresh += 1

        # 새 곡이 없거나 덜 찬 페이지가 나왔으면 끝이다
        if not fresh or any(len(rows) < PAGE_SIZE for rows in pages):
            break

        page += size
        size = PAGE_BATCH

    return list(collected.values())


def find_lyrics(title, singer=""):
    """곡 제목·가수로 검색 결과를 뒤져 가사를 찾는다. 없으면 None.

    가수 검색을 먼저 쓴다 — 금영 곡명 검색은 긴 일본어 제목에서 0건을
    돌려주는 일이 잦은데(실측: `夜に駆ける` 0건, `YOASOBI` 15건) 가수명은
    짧아서 그 문제를 덜 탄다. 그래도 못 찾으면 곡명으로 한 번 더 본다.
    """
    target = normalize_text(title)
    if not target:
        return None

    attempts = []
    if singer:
        attempts.append((CATEGORY["singer"], singer, LYRICS_MAX_PAGES))
    attempts.append((CATEGORY["song"], title, 1))

    for category, keyword, max_pages in attempts:
        for page in range(1, max_pages + 1):
            try:
                blocks = _row_blocks(_fetch(keyword, category, page))
                # search()와 같은 이유로 첫 페이지가 비면 한 번 더 본다 —
                # 금영은 부하가 걸리면 결과 없는 페이지를 간헐적으로 돌려준다.
                # 이걸 진짜 0건으로 받아들이면 '가사 없음'이 하루 동안 캐시된다.
                if page == 1 and not blocks:
                    blocks = _row_blocks(_fetch(keyword, category, 1))
            except KysingError as exc:
                logger.info("금영 가사 조회 실패 (%s): %s", keyword, exc)
                break

            for cells in blocks:
                row_title, row_singer = _title_singer(cells)
                if normalize_text(row_title) != target:
                    continue

                lines = _parse_lyrics(cells[2])
                if lines:
                    return {"title": row_title, "singer": row_singer, "lines": lines}

            # 덜 찬 페이지면 마지막이다
            if len(blocks) < PAGE_SIZE:
                break

    return None
