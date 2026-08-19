"""가사 — 금영 공식 사이트.

금영은 검색 결과 HTML 안에 가사 전문을 함께 실어 보낸다. 키도, 요금도,
별도 요청도 필요 없고 **한글 발음까지 붙어 온다** — 일본어를 못 읽어도
따라 부를 수 있어서, 이 서비스에는 가사 전문 API보다 잘 맞는다.

다만 금영에 없는 곡은 방법이 없다. 실측한 일본곡 7,619곡 중 41%가
태진에만 있고, 태진은 어디에도 가사를 두지 않는다. 그런 곡은 가사 대신
검색 링크를 내보내서 사용자가 직접 찾아가게 한다.
(왜 위키를 직접 연결하지 않는지는 DECISIONS.md 참고 — 문서 주소가
제목과 무관한 영어 슬러그라 미리 매핑을 만들어야 한다.)

⚠️ **권리 확인이 끝나지 않았다 (DECISIONS.md 37번).** 가사는 어문저작물이고
금영이 자기 사이트에 띄우는 것은 금영이 계약을 맺었기 때문이다. 태진·금영에
이용 가능 범위를 문의해 둔 상태이며(`docs/inquiry-catalog.md`), 안 된다는
회신이 오면 `LYRICS_ENABLED=false`로 가사만 즉시 끌 수 있다.
"""

import logging
from urllib.parse import quote_plus

from flask import current_app

from app.services import kysing
from app.utils import cache
from app.utils.normalize import normalize_text

logger = logging.getLogger(__name__)

CACHE_TTL = 30 * 24 * 60 * 60
# 없다고 판정한 것도 캐시한다. 금영 조회가 느려서(2초+) 매번 되묻기엔 비싸다.
# 다만 나중에 금영에 실릴 수 있으니 짧게 잡는다.
EMPTY_CACHE_TTL = 24 * 60 * 60

PROVIDER = "금영"


def is_enabled():
    """가사는 금영 스크래퍼에 얹혀 있다. 그쪽이 꺼지면 같이 꺼진다.

    `LYRICS_ENABLED`는 **가사만** 끄는 스위치다. 권리자가 안 된다고 하면
    이것만 내린다 — `KYSING_ENABLED`를 내리면 금영 공식 검색까지 꺼져서
    최신곡이 통째로 사라진다 (5번).
    """
    return bool(
        current_app.config.get("KYSING_ENABLED")
        and current_app.config.get("LYRICS_ENABLED")
    )


def search_url(title, singer=""):
    """가사를 못 찾았을 때 내보낼 검색 링크.

    곡마다 미리 만들어 둘 필요 없이 누를 때 주소만 조립하면 된다.
    제목을 따옴표로 묶어야 비슷한 제목에 묻히지 않는다.
    """
    query = " ".join(part for part in (f'"{title}"', singer, "가사") if part)
    return f"https://www.google.com/search?q={quote_plus(query)}"


def find(title, singer=""):
    """가사를 반환한다. 실패해도 예외를 던지지 않는다.

    항상 `search_url`을 함께 준다 — 가사를 찾았든 못 찾았든 화면에서
    '인터넷에서 찾아보기'를 띄울 수 있어야 하기 때문이다.
    """
    title = (title or "").strip()
    singer = (singer or "").strip()

    if not title:
        return {"available": False, "reason": "곡 제목이 없어요."}

    link = search_url(title, singer)

    if not is_enabled():
        return {"available": False, "reason": "가사를 가져오지 못했어요.", "search_url": link}

    cache_key = cache.make_key("lyrics", normalize_text(title), normalize_text(singer))
    cached = cache.get_json(cache_key)
    if cached is not None:
        return {**cached, "search_url": link, "cached": True}

    try:
        found = kysing.find_lyrics(title, singer)
    except Exception as exc:
        # 스크래퍼가 예상 못 한 형태를 만났을 때. 링크만이라도 내보낸다.
        logger.warning("금영 가사 조회 실패 (%s / %s): %s", title, singer, exc)
        return {"available": False, "reason": "가사를 가져오지 못했어요.", "search_url": link}

    if not found:
        result = {"available": False, "reason": "금영에 등록된 가사가 없어요."}
        cache.set_json(cache_key, result, ttl=EMPTY_CACHE_TTL)
        return {**result, "search_url": link, "cached": False}

    result = {
        "available": True,
        # [{ko: 한글 발음, ja: 일본어 원문}, ...]
        "lines": found["lines"],
        "provider": PROVIDER,
        "matched_title": found["title"],
        "matched_singer": found["singer"],
    }
    cache.set_json(cache_key, result, ttl=CACHE_TTL)
    return {**result, "search_url": link, "cached": False}
