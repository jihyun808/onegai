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

    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def hit(bucket, limit, window):
    client = cache.get_client()
    if client is None:
        return

    key = cache.make_key("rate", bucket, client_ip())

    try:
        used = client.incr(key)
        if used == 1:
            client.expire(key, window)
        if used > limit:
            raise RateLimited(client.ttl(key) or window)
    except RateLimited:
        raise
    except Exception as exc:
        logger.warning("요청 제한 확인 실패, 통과시킵니다: %s", exc)


def rate_limit(limit, window=60, bucket=None):

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
