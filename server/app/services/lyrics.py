import logging
from urllib.parse import quote_plus

from flask import current_app

from app.services import kysing
from app.utils import cache
from app.utils.normalize import normalize_text

logger = logging.getLogger(__name__)

CACHE_TTL = 30 * 24 * 60 * 60
EMPTY_CACHE_TTL = 24 * 60 * 60

PROVIDER = "금영"


def is_enabled():

    return bool(
        current_app.config.get("KYSING_ENABLED")
        and current_app.config.get("LYRICS_ENABLED")
    )


def search_url(title, singer=""):

    query = " ".join(part for part in (f'"{title}"', singer, "가사") if part)
    return f"https://www.google.com/search?q={quote_plus(query)}"


def find(title, singer=""):

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
        logger.warning("금영 가사 조회 실패 (%s / %s): %s", title, singer, exc)
        return {"available": False, "reason": "가사를 가져오지 못했어요.", "search_url": link}

    if not found:
        result = {"available": False, "reason": "금영에 등록된 가사가 없어요."}
        cache.set_json(cache_key, result, ttl=EMPTY_CACHE_TTL)
        return {**result, "search_url": link, "cached": False}

    result = {
        "available": True,
        "lines": found["lines"],
        "provider": PROVIDER,
        "matched_title": found["title"],
        "matched_singer": found["singer"],
    }
    cache.set_json(cache_key, result, ttl=CACHE_TTL)
    return {**result, "search_url": link, "cached": False}
