"""IP 단위 요청 제한.

계정당 로그인 5회 제한(auth_service)과는 역할이 다르다.
그쪽은 '이 계정을 노린 대입'을 막고, 이쪽은 '한 곳에서 쏟아내는 요청'을 막는다.
아이디를 바꿔가며 시도하면 계정 카운터는 안 오르므로 둘 다 필요하다.

**Redis가 없으면 통과시킨다(fail open).** 캐시 장애로 로그인이 막히는 것보다는
잠시 제한이 풀리는 편이 낫다고 봤다. 반대로 fail closed로 하면 Redis가
죽는 순간 서비스 전체가 멈춘다.
"""

import logging
from functools import wraps

from flask import jsonify, request

from app.utils import cache

logger = logging.getLogger(__name__)


class RateLimited(Exception):
    def __init__(self, retry_after):
        super().__init__("요청이 너무 잦아요. 잠시 후 다시 시도해 주세요.")
        self.retry_after = retry_after


def client_ip():
    """프록시 뒤에 있을 때를 대비해 X-Forwarded-For를 먼저 본다.

    주의: 이 헤더는 위조할 수 있다. 신뢰할 수 있는 프록시 뒤에서만 의미가 있다.
    배포 시 리버스 프록시가 이 헤더를 덮어쓰도록 설정해야 한다.
    """
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def hit(bucket, limit, window):
    """호출 횟수를 하나 올린다. 넘으면 RateLimited를 던진다."""
    client = cache.get_client()
    if client is None:
        return  # Redis 없음 → 제한하지 않는다

    key = cache.make_key("rate", bucket, client_ip())

    try:
        used = client.incr(key)
        if used == 1:
            # 첫 요청에만 만료를 건다. 매번 걸면 창이 계속 밀려 영원히 안 풀린다.
            client.expire(key, window)
        if used > limit:
            raise RateLimited(client.ttl(key) or window)
    except RateLimited:
        raise
    except Exception as exc:
        logger.warning("요청 제한 확인 실패, 통과시킵니다: %s", exc)


def rate_limit(limit, window=60, bucket=None):
    """라우트에 붙이는 데코레이터."""

    def decorate(view):
        name = bucket or view.__name__

        @wraps(view)
        def wrapper(*args, **kwargs):
            try:
                hit(name, limit, window)
            except RateLimited as exc:
                response = jsonify(
                    {"error": "rate_limited", "message": str(exc)}
                )
                response.headers["Retry-After"] = str(exc.retry_after)
                return response, 429
            return view(*args, **kwargs)

        return wrapper

    return decorate
