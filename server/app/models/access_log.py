import logging

from app.utils import db

logger = logging.getLogger(__name__)

RETENTION_DAYS = 400

_INSERT = """
    INSERT INTO access_log (user_id, action, ip, status)
    VALUES (%s, %s, %s, %s)
"""

_PURGE = "DELETE FROM access_log WHERE created_at < NOW() - INTERVAL %s DAY"


def record(user_id, action, ip, status):
    try:
        db.execute_many(_INSERT, [(user_id, action[:80], (ip or "")[:45], status)])
    except Exception as exc:
        logger.warning("접속기록을 남기지 못했습니다 (%s): %s", action, exc)


def purge(days=RETENTION_DAYS):

    return db.execute_many(_PURGE, [(days,)])


def recent(user_id=None, limit=50):
    if user_id is None:
        rows = db.query(
            "SELECT * FROM access_log ORDER BY created_at DESC LIMIT %s", (limit,)
        )
    else:
        rows = db.query(
            "SELECT * FROM access_log WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
            (user_id, limit),
        )
    return rows or []
