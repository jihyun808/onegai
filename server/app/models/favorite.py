"""favorites 테이블.

저장 단위는 **브랜드별 곡번호 하나**다 (`user_id, brand, song_no`).
화면에서는 곡 단위로 묶어 보여주지만, 태진과 금영은 번호가 따로라
한쪽만 담는 경우도 있어서 행을 나눠 둔다.
"""

import logging

from app.utils import db

logger = logging.getLogger(__name__)


def _as_entry(row):
    return {
        "brand": row["brand"],
        "no": row["song_no"],
        "title": row["title"],
        "singer": row["singer"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


def list_for(user_id):
    """담아둔 곡들. DB를 못 쓰면 None."""
    rows = db.query(
        """
        SELECT brand, song_no, title, singer, created_at
        FROM favorites WHERE user_id = %s
        ORDER BY created_at DESC, id DESC
        """,
        (user_id,),
    )
    if rows is None:
        return None
    return [_as_entry(row) for row in rows]


def add_many(user_id, entries):
    """여러 곡을 담는다. 이미 있으면 무시한다. 반영된 행 수."""
    rows = [
        (
            user_id,
            (e.get("brand") or "")[:20],
            (e.get("no") or "")[:20],
            (e.get("title") or "")[:255],
            (e.get("singer") or "")[:255],
        )
        for e in entries
        if e.get("brand") and e.get("no")
    ]
    if not rows:
        return 0

    # UNIQUE (user_id, brand, song_no) 덕분에 중복은 조용히 무시된다
    return db.execute_many(
        """
        INSERT IGNORE INTO favorites (user_id, brand, song_no, title, singer)
        VALUES (%s, %s, %s, %s, %s)
        """,
        rows,
    )


def remove(user_id, brand, song_no):
    return db.execute_many(
        "DELETE FROM favorites WHERE user_id = %s AND brand = %s AND song_no = %s",
        [(user_id, brand, song_no)],
    )


def clear(user_id):
    """담아둔 곡을 모두 지운다."""
    return db.execute_many("DELETE FROM favorites WHERE user_id = %s", [(user_id,)])
