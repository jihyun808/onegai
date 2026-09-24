import logging

import requests
from flask import current_app

from app.utils import cache
from app.utils.normalize import normalize_text

logger = logging.getLogger(__name__)

SEARCH_URL = "https://itunes.apple.com/search"

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
            score = 0
        elif target in track or track in target:
            score = 1
        else:
            continue
        if singer and (normalize_text(singer) in artist or artist in normalize_text(singer)):
            score -= 0.5
        scored.append((score, item))

    if not scored:
        return None
    return min(scored, key=lambda x: x[0])[1]


def find(title, singer=""):
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
        "artwork_url": artwork.replace("100x100bb", "300x300bb"),
        "track_url": match.get("trackViewUrl", ""),
    }
    cache.set_json(cache_key, result, ttl=CACHE_TTL)
    return {**result, "cached": False}
