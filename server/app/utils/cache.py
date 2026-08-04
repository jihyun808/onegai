"""Redis 캐시 래퍼.

manana API는 하루 1회 갱신되므로 기본 TTL은 24시간이다.
Redis에 접속할 수 없어도 검색 자체는 동작해야 하므로
모든 캐시 실패는 삼켜지고 miss 로 취급한다.
"""

import json
import logging
import time

import redis
from flask import current_app

logger = logging.getLogger(__name__)

_client = None
_retry_after = 0.0

# 캐시에는 정규화를 마친 결과(match_key 포함)가 들어간다.
# normalize.py의 규칙을 바꾸면 기존 캐시가 옛 키를 물고 있으므로
# 버전을 올려서 무효화한다.
CACHE_VERSION = "v3"
CACHE_PREFIX = f"kada:search:{CACHE_VERSION}"

# 업스트림이 모두 실패했을 때 내보낼 비상용 사본의 수명.
# 정상 TTL보다 훨씬 길게 잡아, 오래된 결과라도 빈 화면보다는 낫게 한다.
STALE_TTL = 7 * 24 * 60 * 60

# 연결 실패 후 재시도까지 기다리는 시간.
# 매 요청마다 재연결을 시도하면 Redis가 죽었을 때 응답이 느려지고,
# 영구히 포기하면 나중에 Redis를 띄워도 캐시가 살아나지 않는다.
RETRY_INTERVAL = 30


def get_client():
    """앱 설정 기반 Redis 클라이언트. 연결 불가 시 None."""
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
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        client.ping()
    except Exception as exc:  # 연결 실패 시 캐시 없이 계속 동작
        logger.warning(
            "Redis 연결 실패, %d초간 캐시 없이 동작합니다: %s", RETRY_INTERVAL, exc
        )
        _retry_after = time.monotonic() + RETRY_INTERVAL
        return None

    _client = client
    return _client


def reset_client():
    """테스트/재설정용. 캐시된 클라이언트를 버린다."""
    global _client, _retry_after
    _client = None
    _retry_after = 0.0


def is_alive():
    """실제로 ping 해서 살아있는지 확인한다.

    get_client()는 캐시된 커넥션 객체를 그대로 돌려주므로
    Redis가 중간에 죽어도 즉시 알 수 없다. 헬스체크는 매번 확인한다.
    """
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
    """살아있던 Redis가 죽은 경우. 클라이언트를 버리고 재시도 시각을 뒤로 민다."""
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
    """정상 캐시와 함께, 훨씬 오래 사는 '비상용' 사본을 남긴다.

    업스트림이 죽었을 때 빈 화면 대신 지난 결과라도 보여주기 위한 완충재다.
    TTL이 지나도 stale 사본은 남아 있으므로 get_stale()로 꺼내 쓴다.
    """
    set_json(key, value, ttl=ttl)
    set_json(stale_key(key), value, ttl=stale_ttl or STALE_TTL)


def get_stale(key):
    return get_json(stale_key(key))


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
