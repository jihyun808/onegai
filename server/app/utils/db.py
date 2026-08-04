"""MySQL 커넥션 풀.

Redis와 같은 원칙을 따른다 — **DB가 없어도 서비스는 돌아간다.**
연결에 실패하면 None을 돌려주고, 검색은 기존대로 외부 사이트를 직접 본다.
느려질 뿐 멈추지는 않는다.
"""

import logging
import time

import mysql.connector
from flask import current_app
from mysql.connector import pooling

logger = logging.getLogger(__name__)

_pool = None
_retry_after = 0.0

# 연결 실패 후 재시도까지 기다리는 시간.
# 매 요청마다 재연결을 시도하면 DB가 죽었을 때 응답이 느려진다.
RETRY_INTERVAL = 30


def get_pool():
    """커넥션 풀. 연결 불가 시 None."""
    global _pool, _retry_after

    if _pool is not None:
        return _pool
    if time.monotonic() < _retry_after:
        return None

    config = current_app.config
    try:
        _pool = pooling.MySQLConnectionPool(
            pool_name="kada",
            pool_size=config["MYSQL_POOL_SIZE"],
            host=config["MYSQL_HOST"],
            port=config["MYSQL_PORT"],
            user=config["MYSQL_USER"],
            password=config["MYSQL_PASSWORD"],
            database=config["MYSQL_DATABASE"],
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            # mysql-connector는 초 단위 정수만 받는다 (float를 주면 TypeError)
            connection_timeout=int(config["MYSQL_TIMEOUT"]),
            autocommit=True,
        )
    except Exception as exc:
        logger.warning(
            "MySQL 연결 실패, %d초간 DB 없이 동작합니다: %s", RETRY_INTERVAL, exc
        )
        _retry_after = time.monotonic() + RETRY_INTERVAL
        return None

    return _pool


def reset_pool():
    """테스트/재설정용."""
    global _pool, _retry_after
    _pool = None
    _retry_after = 0.0


def _drop_pool():
    """살아있던 DB가 죽은 경우. 풀을 버리고 재시도 시각을 미룬다."""
    global _pool, _retry_after
    _pool = None
    _retry_after = time.monotonic() + RETRY_INTERVAL


def query(sql, params=None):
    """SELECT. 실패하면 None (빈 결과와 구분해야 폴백 판단이 된다)."""
    pool = get_pool()
    if pool is None:
        return None

    try:
        conn = pool.get_connection()
    except Exception as exc:
        logger.warning("커넥션 획득 실패: %s", exc)
        _drop_pool()
        return None

    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute(sql, params or ())
            return cursor.fetchall()
    except mysql.connector.Error as exc:
        logger.warning("쿼리 실패: %s", exc)
        _drop_pool()
        return None
    finally:
        conn.close()


def execute_many(sql, rows):
    """대량 INSERT/UPDATE. 반영된 행 수를 돌려준다. 실패하면 0."""
    if not rows:
        return 0

    pool = get_pool()
    if pool is None:
        return 0

    try:
        conn = pool.get_connection()
    except Exception as exc:
        logger.warning("커넥션 획득 실패: %s", exc)
        _drop_pool()
        return 0

    try:
        with conn.cursor() as cursor:
            cursor.executemany(sql, rows)
            return cursor.rowcount
    except mysql.connector.Error as exc:
        logger.warning("일괄 실행 실패: %s", exc)
        _drop_pool()
        return 0
    finally:
        conn.close()


def is_alive():
    """실제로 한 번 찔러본다. 헬스체크용."""
    result = query("SELECT 1 AS ok")
    return bool(result)
