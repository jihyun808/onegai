import logging
import time

import mysql.connector
from flask import current_app
from mysql.connector import pooling

logger = logging.getLogger(__name__)

_pool = None
_retry_after = 0.0

RETRY_INTERVAL = 30


def get_pool():
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
    global _pool, _retry_after
    _pool = None
    _retry_after = 0.0


def _drop_pool():
    global _pool, _retry_after
    _pool = None
    _retry_after = time.monotonic() + RETRY_INTERVAL


def query(sql, params=None):
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
    result = query("SELECT 1 AS ok")
    return bool(result)
