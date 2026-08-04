"""가사 — Musixmatch API.

곡명 + 가수명으로 가사를 찾는다.

**주의:** Musixmatch는 오류일 때도 HTTP 200을 준다. 실제 상태는
응답 본문의 message.header.status_code에 들어 있으므로 그걸 봐야 한다.

무료 플랜은 가사 전문이 아니라 **앞부분 30% 발췌**만 준다.
전문 표시는 상위 플랜이 필요하다.

키가 없으면 기능만 꺼진다.
"""

import logging

import requests
from flask import current_app

from app.utils import cache
from app.utils.normalize import normalize_text

logger = logging.getLogger(__name__)

BASE_URL = "https://api.musixmatch.com/ws/1.1/matcher.lyrics.get"

CACHE_TTL = 30 * 24 * 60 * 60
EMPTY_CACHE_TTL = 24 * 60 * 60


def is_enabled():
    return bool(current_app.config.get("MUSIXMATCH_API_KEY"))


def find(title, singer=""):
    """가사를 반환한다. 실패해도 예외를 던지지 않는다."""
    title = (title or "").strip()
    if not title:
        return {"available": False, "reason": "곡 제목이 없어요."}

    key = current_app.config.get("MUSIXMATCH_API_KEY")
    if not key:
        return {"available": False, "reason": "가사 기능이 설정되지 않았어요."}

    singer = (singer or "").strip()
    cache_key = cache.make_key("lyrics", normalize_text(title), normalize_text(singer))
    cached = cache.get_json(cache_key)
    if cached is not None:
        return {**cached, "cached": True}

    try:
        response = requests.get(
            BASE_URL,
            params={"q_track": title, "q_artist": singer, "apikey": key},
            timeout=current_app.config["MUSIXMATCH_TIMEOUT"],
        )
        response.raise_for_status()
        payload = response.json()["message"]
        status = payload["header"]["status_code"]
    except Exception as exc:
        logger.warning("Musixmatch 호출 실패: %s", exc)
        return {"available": False, "reason": "가사를 가져오지 못했어요."}

    if status == 401:
        logger.error("Musixmatch 인증 실패 — API 키를 확인하세요")
        return {"available": False, "reason": "가사 기능이 설정되지 않았어요."}

    if status == 402:
        return {"available": False, "reason": "이번 달 가사 조회 한도를 다 썼어요."}

    if status != 200:
        result = {"available": False, "reason": "가사를 찾지 못했어요."}
        cache.set_json(cache_key, result, ttl=EMPTY_CACHE_TTL)
        return {**result, "cached": False}

    body = payload.get("body") or {}
    lyrics = (body.get("lyrics") or {}).get("lyrics_body", "").strip()

    if not lyrics:
        result = {"available": False, "reason": "가사를 찾지 못했어요."}
        cache.set_json(cache_key, result, ttl=EMPTY_CACHE_TTL)
        return {**result, "cached": False}

    # 무료 플랜은 본문 끝에 상업적 이용 금지 문구를 붙여 보낸다.
    # 화면에는 가사만 남기고, 출처 표기는 별도 필드로 내보낸다.
    tracking = (body.get("lyrics") or {}).get("script_tracking_url", "")
    marker = "***"
    if marker in lyrics:
        lyrics = lyrics.split(marker)[0].strip()

    result = {
        "available": True,
        "lyrics": lyrics,
        # 무료 플랜은 발췌본이다. UI에서 "일부만 제공" 안내에 쓴다.
        "partial": True,
        "provider": "Musixmatch",
        "tracking_url": tracking,
    }
    cache.set_json(cache_key, result, ttl=CACHE_TTL)
    return {**result, "cached": False}
