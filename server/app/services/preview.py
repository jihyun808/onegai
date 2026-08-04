"""미리듣기 — iTunes Search API.

곡명 + 가수명으로 검색해 30초 프리뷰 URL과 앨범아트를 가져온다.

**공식 Apple Music API 대신 iTunes Search API를 쓴다.**
Apple Music API는 유료 개발자 계정으로 발급한 JWT 토큰이 필요하고
키 없이는 401이다. iTunes Search API는 키가 필요 없고 같은 프리뷰 URL을 준다.

키가 필요 없으므로 이 기능은 항상 켜져 있다.
"""

import logging

import requests
from flask import current_app

from app.utils import cache
from app.utils.normalize import normalize_text

logger = logging.getLogger(__name__)

SEARCH_URL = "https://itunes.apple.com/search"

# 일본곡이 대상이므로 일본 스토어를 본다. 없으면 미국 스토어로 한 번 더.
COUNTRIES = ("JP", "US")

CACHE_TTL = 7 * 24 * 60 * 60
EMPTY_CACHE_TTL = 24 * 60 * 60


def _request(term, country, limit):
    response = requests.get(
        SEARCH_URL,
        params={
            "term": term,
            "media": "music",
            "entity": "song",
            "country": country,
            "limit": limit,
        },
        timeout=current_app.config["ITUNES_TIMEOUT"],
    )
    response.raise_for_status()
    return response.json().get("results", [])


def _pick(results, title, singer):
    """제목이 가장 잘 맞는 트랙을 고른다.

    iTunes는 느슨하게 매칭하므로 첫 결과가 엉뚱한 곡일 수 있다.
    검색 결과를 우리 정규화 규칙으로 비교해 걸러낸다.
    """
    target = normalize_text(title)
    if not target:
        return None

    scored = []
    for item in results:
        if not item.get("previewUrl"):
            continue
        track = normalize_text(item.get("trackName", ""))
        artist = normalize_text(item.get("artistName", ""))
        if track == target:
            score = 0  # 제목 완전 일치
        elif target in track or track in target:
            score = 1
        else:
            continue
        # 가수까지 맞으면 우선순위를 올린다
        if singer and (normalize_text(singer) in artist or artist in normalize_text(singer)):
            score -= 0.5
        scored.append((score, item))

    if not scored:
        return None
    return min(scored, key=lambda x: x[0])[1]


def find(title, singer=""):
    """프리뷰 정보를 반환한다. 실패해도 예외를 던지지 않는다."""
    title = (title or "").strip()
    if not title:
        return {"available": False, "reason": "곡 제목이 없어요."}

    singer = (singer or "").strip()
    cache_key = cache.make_key("preview", normalize_text(title), normalize_text(singer))
    cached = cache.get_json(cache_key)
    if cached is not None:
        return {**cached, "cached": True}

    term = f"{singer} {title}".strip()
    match = None
    try:
        for country in COUNTRIES:
            match = _pick(_request(term, country, 12), title, singer)
            if match:
                break
    except Exception as exc:
        logger.warning("iTunes 조회 실패: %s", exc)
        return {"available": False, "reason": "미리듣기를 가져오지 못했어요."}

    if not match:
        result = {"available": False, "reason": "미리듣기를 찾지 못했어요."}
        cache.set_json(cache_key, result, ttl=EMPTY_CACHE_TTL)
        return {**result, "cached": False}

    artwork = match.get("artworkUrl100", "")
    result = {
        "available": True,
        "title": match.get("trackName", ""),
        "singer": match.get("artistName", ""),
        "album": match.get("collectionName", ""),
        "preview_url": match.get("previewUrl", ""),
        # 100px 썸네일 URL의 치수를 바꾸면 더 큰 이미지를 받을 수 있다
        "artwork_url": artwork.replace("100x100bb", "300x300bb"),
        "track_url": match.get("trackViewUrl", ""),
    }
    cache.set_json(cache_key, result, ttl=CACHE_TTL)
    return {**result, "cached": False}
