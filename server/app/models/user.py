import logging

from app.utils import db

logger = logging.getLogger(__name__)


def _as_public(row):
    return {
        "id": row["id"],
        "username": row["username"],
        "avatar": row.get("avatar") or None,
    }


def find_by_username(username):
    rows = db.query(
        "SELECT id, username, password_hash, avatar FROM users WHERE username = %s",
        (username,),
    )
    if rows is None:
        return False
    return rows[0] if rows else None


def exists(username):
    found = find_by_username(username)
    if found is False:
        return None
    return found is not None


def create(username, password_hash):
    affected = db.execute_many(
        "INSERT IGNORE INTO users (username, password_hash, nickname) VALUES (%s, %s, %s)",
        [(username, password_hash, username)],
    )
    if not affected:
        return None

    found = find_by_username(username)
    return _as_public(found) if found else None


def get(user_id):
    rows = db.query(
        "SELECT id, username, avatar FROM users WHERE id = %s", (user_id,)
    )
    if not rows:
        return None
    return _as_public(rows[0])


def update_profile(user_id, username=None, avatar=None):
    sets, params = [], []
    if username is not None:
        sets.append("username = %s")
        params.append(username)
    if avatar is not None:
        sets.append("avatar = %s")
        params.append(avatar or None)

    if not sets:
        return get(user_id)

    params.append(user_id)
    affected = db.execute_many(
        f"UPDATE IGNORE users SET {', '.join(sets)} WHERE id = %s", [tuple(params)]
    )
    current = get(user_id)
    if username is not None and current and current["username"] != username:
        return None
    if affected == 0 and username is not None and current is None:
        return None
    return current


def delete(user_id):
    return db.execute_many("DELETE FROM users WHERE id = %s", [(user_id,)])
