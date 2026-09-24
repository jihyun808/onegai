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
    return db.execute_many("DELETE FROM favorites WHERE user_id = %s", [(user_id,)])
