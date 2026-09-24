import logging
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode

import requests
from flask import current_app

from app.utils.normalize import normalize_text

logger = logging.getLogger(__name__)

BASE_URL = "https://kysing.kr/search/"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

CATEGORY = {"song": 2, "singer": 7, "lyrics": 4, "no": 1}

PAGE_SIZE = 15
MAX_PAGES = 20
PAGE_BATCH = 3

_ROW_BLOCK = re.compile(r'<ul class="search_chart_list clear">(.*?)</ul>', re.S)
_CELL = re.compile(r"<li[^>]*>(.*?)</li>", re.S)
_TAG = re.compile(r"<[^>]+>")

_LYRICS_SPLIT = re.compile(r"\s*닫기\s*")

_LYRICS_CONT = re.compile(r'<div class="LyricsCont">(.*?)</div>', re.S)
_LYRICS_TIT = re.compile(r'<p class="LyricsTit">.*?</p>', re.S)
_BR = re.compile(r"<br\s*/?>", re.I)

_HANGUL = re.compile(r"[가-힣]")
_RUBY = re.compile(r"^(?=[^/]*/)[ぁ-ゖー/\s]*$")

LYRICS_MAX_PAGES = 4

_RELEASE = re.compile(r"^(\d{4})\.(\d{1,2})$")


class KysingError(Exception):
    pass


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
    blocks = []
    for block in _ROW_BLOCK.findall(page_html)[1:]:
        cells = _CELL.findall(block)
        if len(cells) >= 7:
            blocks.append(cells)
    return blocks


def _title_singer(cells):
    title = _LYRICS_SPLIT.split(_text(cells[2]))[0]
    singer = _text(cells[3])
    if singer and title.endswith(singer):
        title = title[: -len(singer)].strip()
    return title, singer


def _parse(page_html):
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
    category = CATEGORY.get(search_type)
    if category is None:
        raise ValueError(f"지원하지 않는 검색 타입입니다: {search_type}")

    first = _parse(_fetch(keyword, category, 1))

    if not first:
        first = _parse(_fetch(keyword, category, 1))

    collected = {row["no"]: row for row in first}
    if len(first) < PAGE_SIZE:
        return list(collected.values())

    app = current_app._get_current_object()

    def fetch_page(page):
        with app.app_context():
            try:
                return _parse(_fetch(keyword, category, page))
            except KysingError as exc:
                logger.info("금영 %d페이지 실패, 여기까지만 씁니다: %s", page, exc)
                return []

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

        if not fresh or any(len(rows) < PAGE_SIZE for rows in pages):
            break

        page += size
        size = PAGE_BATCH

    return list(collected.values())


def find_lyrics(title, singer=""):

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

            if len(blocks) < PAGE_SIZE:
                break

    return None
