import logging

import requests
from flask import current_app

from app.utils import cache

logger = logging.getLogger(__name__)

FREE_URL = "https://api-free.deepl.com/v2/translate"
PRO_URL = "https://api.deepl.com/v2/translate"

CACHE_TTL = 30 * 24 * 60 * 60

MAX_TEXT_LENGTH = 200

BATCH_SIZE = 50


def is_enabled():
    return bool(current_app.config.get("DEEPL_API_KEY"))


def _endpoint(key):
    return FREE_URL if key.endswith(":fx") else PRO_URL


def translate(text, target_lang="KO", source_lang="JA"):
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


def translate_many(texts, target_lang="KO", source_lang="JA"):


    texts = [t.strip()[:MAX_TEXT_LENGTH] for t in texts if (t or "").strip()]
    if not texts:
        return [], None

    key = current_app.config.get("DEEPL_API_KEY")
    if not key:
        return [], "번역 기능이 설정되지 않았어요."

    try:
        response = requests.post(
            _endpoint(key),
            headers={"Authorization": f"DeepL-Auth-Key {key}"},
            data={
                "text": texts,
                "target_lang": target_lang,
                "source_lang": source_lang,
            },
            timeout=current_app.config["DEEPL_TIMEOUT"] * 3,
        )
        response.raise_for_status()
        got = [t["text"] for t in response.json()["translations"]]
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else 0
        if status == 456:
            return [], "이번 달 번역 한도를 다 썼어요."
        logger.warning("DeepL 일괄 호출 실패 (HTTP %s)", status)
        return [], f"번역 호출이 실패했어요 (HTTP {status})."
    except Exception as exc:
        logger.warning("DeepL 일괄 호출 실패: %s", exc)
        return [], "번역 호출이 실패했어요."

    if len(got) != len(texts):
        logger.error("DeepL 응답 개수 불일치: %d개 보내고 %d개 받음", len(texts), len(got))
        return [], "번역 결과 수가 맞지 않아요."

    return list(zip(texts, got)), None
