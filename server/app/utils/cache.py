import json
import logging
import time

import redis
from flask import current_app

logger = logging.getLogger(__name__)

_client = None
_retry_after = 0.0

CACHE_VERSION = "v3"
CACHE_PREFIX = f"kada:search:{CACHE_VERSION}"

STALE_TTL = 7 * 24 * 60 * 60

RETRY_INTERVAL = 30


def get_client():
    global _client, _retry_after

    if _client is not None:
        return _client
    if time.monotonic() < _retry_after:
        return None

    try:
        client = redis.Redis(
            host=current_app.config["REDIS_HOST"],
            port=current_app.config["REDIS_PORT"],
            db=current_app.config["REDIS_DB"],
            password=current_app.config["REDIS_PASSWORD"],
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        client.ping()
    except Exception as exc:
        logger.warning(
            "Redis 연결 실패, %d초간 캐시 없이 동작합니다: %s", RETRY_INTERVAL, exc
        )
        _retry_after = time.monotonic() + RETRY_INTERVAL
        return None

    _client = client
    return _client


def reset_client():
    global _client, _retry_after
    _client = None
    _retry_after = 0.0


def is_alive():

    client = get_client()
    if client is None:
        return False

    try:
        client.ping()
        return True
    except Exception:
        _drop_client()
        return False


def _drop_client():
    global _client, _retry_after
    _client = None
    _retry_after = time.monotonic() + RETRY_INTERVAL


def make_key(*parts):
    return ":".join([CACHE_PREFIX, *(str(p) for p in parts)])


def get_json(key):
    client = get_client()
    if client is None:
        return None

    try:
        raw = client.get(key)
    except Exception as exc:
        logger.warning("캐시 조회 실패 (%s): %s", key, exc)
        _drop_client()
        return None

    if raw is None:
        return None

    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        logger.warning("캐시 값 파싱 실패, 무시합니다: %s", key)
        return None


def stale_key(key):
    return f"{key}:stale"


def set_with_stale(key, value, ttl=None, stale_ttl=None):

    set_json(key, value, ttl=ttl)
    set_json(stale_key(key), value, ttl=stale_ttl or STALE_TTL)


def get_stale(key):
    return get_json(stale_key(key))


def delete(key):
    client = get_client()
    if client is None:
        return False
    try:
        client.delete(key)
        return True
    except Exception as exc:
        logger.warning("캐시 삭제 실패 (%s): %s", key, exc)
        _drop_client()
        return False


def set_json(key, value, ttl=None):
    client = get_client()
    if client is None:
        return False

    if ttl is None:
        ttl = current_app.config["CACHE_TTL"]

    try:
        client.setex(key, ttl, json.dumps(value, ensure_ascii=False))
        return True
    except Exception as exc:
        logger.warning("캐시 저장 실패 (%s): %s", key, exc)
        _drop_client()
        return False
