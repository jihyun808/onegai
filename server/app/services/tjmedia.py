import logging
import re

import requests
from flask import current_app

logger = logging.getLogger(__name__)

BASE_URL = "https://www.tjmedia.com/song/accompaniment_search"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

SEARCH_TYPE = {"song": 1, "singer": 2}


PAGE_SIZE = 15
MAX_PAGES = 20

_ROW_BLOCK = re.compile(
    r'<ul class="grid-container list ico">(.*?)</ul>\s*</li>', re.S
)
_CELL_SPLIT = re.compile(r'<li class="grid-item')
_OPEN_TAG_TAIL = re.compile(r"^[^>]*>")
_TAG = re.compile(r"<[^>]+>")
_INLINE_TAG = re.compile(r"</?(?:span|b|strong|em|i)\b[^>]*>", re.I)
_LABEL = re.compile(r"^(곡번호|곡제목|가수|작사가|작곡가)\s*")


class TjMediaError(Exception):
    pass


def _text(fragment):
    from html import unescape

    fragment = _OPEN_TAG_TAIL.sub("", fragment, count=1)
    fragment = _INLINE_TAG.sub("", fragment)
    return _LABEL.sub("", " ".join(unescape(_TAG.sub(" ", fragment)).split()))


_DEVICE_NOTE = re.compile(r"^\s*\d+\s*이상\s*반주기\s*전용곡\s*")


def _strip_device_note(title):

    return _DEVICE_NOTE.sub("", title).strip()


def _parse(page_html):
    rows = []

    for block in _ROW_BLOCK.findall(page_html):
        cells = [_text(c) for c in _CELL_SPLIT.split(block)[1:]]
        if len(cells) < 3 or not cells[0].isdigit():
            continue

        rows.append(
            {
                "brand": "tj",
                "no": cells[0],
                "title": _strip_device_note(cells[1]),
                "singer": cells[2],
                "lyricist": cells[3] if len(cells) > 3 else "",
                "composer": cells[4] if len(cells) > 4 else "",
                "release": "",
            }
        )

    return rows


def _fetch(keyword, str_type, page):
    try:
        response = requests.get(
            BASE_URL,
            params={
                "pageNo": page,
                "nationType": "",
                "strType": str_type,
                "searchTxt": keyword,
                "strWord": "",
            },
            headers={"User-Agent": USER_AGENT},
            timeout=current_app.config["TJMEDIA_TIMEOUT"],
        )
        response.raise_for_status()
    except requests.Timeout as exc:
        raise TjMediaError("TJ 공식 사이트 응답 시간이 초과되었습니다.") from exc
    except requests.RequestException as exc:
        raise TjMediaError("TJ 공식 사이트 호출에 실패했습니다.") from exc

    return response.text


def search(keyword, search_type="song"):
    str_type = SEARCH_TYPE.get(search_type)
    if str_type is None:
        raise ValueError(f"지원하지 않는 검색 타입입니다: {search_type}")

    collected = {}

    for page in range(1, MAX_PAGES + 1):
        rows = _parse(_fetch(keyword, str_type, page))
        fresh = [row for row in rows if row["no"] not in collected]
        if not fresh:
            break

        for row in fresh:
            collected[row["no"]] = row

        if len(rows) < PAGE_SIZE:
            break

    return list(collected.values())
