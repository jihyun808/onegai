"""TJ 공식 사이트(tjmedia.com) 검색 스크래퍼.

manana도 TJ 곡 수는 거의 따라잡고 있지만(가수당 0~3곡 차이),
**한글 발음 검색이 manana에는 없다.**

    '요루시카' → 공식 15건 / manana 0건
    '요루니카케루' → 공식 1건 (夜に駆ける) / manana 0건

노래방에서 일본곡을 찾는 사람은 한글 발음으로 치는 일이 잦아서
이 차이가 크다. 그래서 금영과 마찬가지로 공식을 먼저 보고 manana로 폴백한다.

공개 API가 아니라 HTML 파싱이다. 구조가 바뀌면 조용히 0건이 되므로
폴백과 헬스체크를 반드시 함께 둔다.

결과 마크업: <ul class="grid-container list ico"> 안의 grid-item 들
    [0] 곡번호  [1] 곡제목  [2] 가수  [3] 작사가  [4] 작곡가
"""

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

# strType: 0 통합 / 1 곡제목 / 2 가수명 / 4 작사가 / 8 작곡가 / 16 곡번호 / 32 메들리
SEARCH_TYPE = {"song": 1, "singer": 2}

# nationType: KOR 가요 / ENG 팝송 / JPN 일본곡 (지금은 안 쓴다 —
# 사용자가 일본어나 일본 가수명으로 검색하면 결과가 이미 일본곡이다)

PAGE_SIZE = 15
MAX_PAGES = 20

_ROW_BLOCK = re.compile(
    r'<ul class="grid-container list ico">(.*?)</ul>\s*</li>', re.S
)
# 칸을 <li>...</li> 로 잡으면 안 된다. 제목 칸(title3) 안에 아이콘용 <ul><li>가
# 중첩돼 있어서, 비탐욕 매칭이 안쪽 </li>에서 끊겨 제목이 통째로 비어버린다.
# 여는 태그를 기준으로 쪼개면 중첩과 무관하게 칸 경계가 맞는다.
_CELL_SPLIT = re.compile(r'<li class="grid-item')
# 쪼갠 조각 앞에는 여는 태그의 나머지(` title3">`)가 남는다
_OPEN_TAG_TAIL = re.compile(r"^[^>]*>")
_TAG = re.compile(r"<[^>]+>")
# 모바일용으로 각 칸 앞에 붙는 라벨. 텍스트로 같이 딸려 오므로 떼어낸다.
_LABEL = re.compile(r"^(곡번호|곡제목|가수|작사가|작곡가)\s*")


class TjMediaError(Exception):
    """TJ 공식 사이트 조회 실패."""


def _text(fragment):
    from html import unescape

    # 여는 태그의 나머지가 앞에 붙어 있으므로 먼저 지운다
    fragment = _OPEN_TAG_TAIL.sub("", fragment, count=1)
    return _LABEL.sub("", " ".join(unescape(_TAG.sub(" ", fragment)).split()))


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
                "title": cells[1],
                "singer": cells[2],
                "lyricist": cells[3] if len(cells) > 3 else "",
                "composer": cells[4] if len(cells) > 4 else "",
                # 공식 검색 결과에는 발매일이 없다.
                # 정렬은 곡번호로 대체된다 (번호가 클수록 최신곡).
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
    """TJ 공식 사이트에서 검색한다. manana와 같은 스키마의 리스트를 반환."""
    str_type = SEARCH_TYPE.get(search_type)
    if str_type is None:
        raise ValueError(f"지원하지 않는 검색 타입입니다: {search_type}")

    collected = {}

    for page in range(1, MAX_PAGES + 1):
        rows = _parse(_fetch(keyword, str_type, page))
        # 마지막 페이지를 넘기면 같은 내용이 반복된다. 새 번호가 없으면 종료.
        fresh = [row for row in rows if row["no"] not in collected]
        if not fresh:
            break

        for row in fresh:
            collected[row["no"]] = row

        if len(rows) < PAGE_SIZE:
            break

    return list(collected.values())
