"""개인정보처리시스템 접속기록 (db/006_access_log.sql).

「개인정보의 안전성 확보조치 기준」 제8조가 요구하는 기록이다.
개인정보에 접근하는 요청만 남기고 1년 이상 보관한다.

**여기서 예외를 밖으로 내지 않는다.** 기록에 실패했다고 이용자의 요청이
실패하면 안 된다. 못 남긴 것은 로그로만 알린다.
"""

import logging

from app.utils import db

logger = logging.getLogger(__name__)

# 제8조는 1년 이상을 요구한다. 넉넉히 잡아도 행이 작아 부담이 없다.
RETENTION_DAYS = 400

_INSERT = """
    INSERT INTO access_log (user_id, action, ip, status)
    VALUES (%s, %s, %s, %s)
"""

_PURGE = "DELETE FROM access_log WHERE created_at < NOW() - INTERVAL %s DAY"


def record(user_id, action, ip, status):
    """접속기록 한 줄. 실패해도 조용히 넘어간다."""
    try:
        db.execute_many(_INSERT, [(user_id, action[:80], (ip or "")[:45], status)])
    except Exception as exc:
        logger.warning("접속기록을 남기지 못했습니다 (%s): %s", action, exc)


def purge(days=RETENTION_DAYS):
    """보관 기간이 지난 기록을 지운다. 지운 행 수.

    **보관 기간을 줄이는 쪽으로 함부로 바꾸면 안 된다** — 법이 정한 하한이
    1년이다. 개인정보 처리방침에 적은 기간과도 맞아야 한다.
    """
    return db.execute_many(_PURGE, [(days,)])


def recent(user_id=None, limit=50):
    """최근 기록. 점검용."""
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
