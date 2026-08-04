"""DeepL 번역.

일본어 곡 제목을 한국어로 옮겨 함께 보여준다.

키가 없으면 기능만 꺼진다. 예외를 던지지 않고 available=False를 돌려주므로
클라이언트는 번역 영역만 감추면 된다.
"""

import logging

import requests
from flask import current_app

from app.utils import cache

logger = logging.getLogger(__name__)

# 무료 키는 ':fx'로 끝난다. 엔드포인트가 다르므로 키를 보고 고른다.
FREE_URL = "https://api-free.deepl.com/v2/translate"
PRO_URL = "https://api.deepl.com/v2/translate"

# 번역 결과는 바뀌지 않는다. 길게 캐싱해 호출량(무료 월 50만자)을 아낀다.
CACHE_TTL = 30 * 24 * 60 * 60

MAX_TEXT_LENGTH = 200


def is_enabled():
    return bool(current_app.config.get("DEEPL_API_KEY"))


def _endpoint(key):
    return FREE_URL if key.endswith(":fx") else PRO_URL


def translate(text, target_lang="KO", source_lang="JA"):
    """번역 결과를 반환한다. 실패해도 예외를 던지지 않는다."""
    text = (text or "").strip()
    if not text:
        return {"available": False, "reason": "번역할 문장이 없어요."}

    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]

    key = current_app.config.get("DEEPL_API_KEY")
    if not key:
        return {"available": False, "reason": "번역 기능이 설정되지 않았어요."}

    cache_key = cache.make_key("translate", target_lang, text)
    cached = cache.get_json(cache_key)
    if cached is not None:
        return {**cached, "cached": True}

    try:
        response = requests.post(
            _endpoint(key),
            headers={"Authorization": f"DeepL-Auth-Key {key}"},
            data={
                "text": text,
                "target_lang": target_lang,
                "source_lang": source_lang,
            },
            timeout=current_app.config["DEEPL_TIMEOUT"],
        )
        response.raise_for_status()
        payload = response.json()
        translated = payload["translations"][0]["text"]
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else 0
        # 456 = 이달 번역 할당량 소진
        reason = (
            "이번 달 번역 한도를 다 썼어요."
            if status == 456
            else "번역을 가져오지 못했어요."
        )
        logger.warning("DeepL 호출 실패 (HTTP %s)", status)
        return {"available": False, "reason": reason}
    except Exception as exc:
        logger.warning("DeepL 호출 실패: %s", exc)
        return {"available": False, "reason": "번역을 가져오지 못했어요."}

    result = {
        "available": True,
        "text": text,
        "translated": translated,
        "target_lang": target_lang,
    }
    cache.set_json(cache_key, result, ttl=CACHE_TTL)
    return {**result, "cached": False}
