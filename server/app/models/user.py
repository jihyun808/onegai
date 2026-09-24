"""users 테이블 조회/생성.

비밀번호는 **절대 평문으로 다루지 않는다.** bcrypt 해시만 저장하고,
조회 결과에도 해시를 담아 내보내지 않는다.
"""

import logging

from app.utils import db

logger = logging.getLogger(__name__)


def _as_public(row):
    """화면에 내보낼 형태. password_hash는 절대 포함하지 않는다."""
    return {
        "id": row["id"],
        "username": row["username"],
        "avatar": row.get("avatar") or None,
    }


def find_by_username(username):
    """아이디로 찾는다. 없으면 None, DB 장애면 False로 구분한다."""
    rows = db.query(
        "SELECT id, username, password_hash, avatar FROM users WHERE username = %s",
        (username,),
    )
    if rows is None:
        return False
    return rows[0] if rows else None


def exists(username):
    """아이디가 이미 쓰이는지. DB 장애면 None."""
    found = find_by_username(username)
    if found is False:
        return None
    return found is not None


def create(username, password_hash):
    """새 사용자를 만든다. 아이디가 겹치면 None."""
    # UNIQUE 제약이 최종 방어선이다. 중복 확인과 INSERT 사이에 다른 요청이
    # 끼어들 수 있으므로(경쟁 상태), 여기서 한 번 더 걸리도록 둔다.
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
    """아이디·프로필 이미지를 바꾼다. 아이디가 겹치면 None."""
    sets, params = [], []
    if username is not None:
        sets.append("username = %s")
        params.append(username)
    if avatar is not None:
        # 빈 문자열은 '지우기'로 본다
        sets.append("avatar = %s")
        params.append(avatar or None)

    if not sets:
        return get(user_id)

    params.append(user_id)
    affected = db.execute_many(
        f"UPDATE IGNORE users SET {', '.join(sets)} WHERE id = %s", [tuple(params)]
    )
    # UPDATE IGNORE는 중복이면 0행을 반환한다. 다만 값이 그대로여도 0이라
    # 실제로 바뀌었는지는 다시 읽어 확인한다.
    current = get(user_id)
    if username is not None and current and current["username"] != username:
        return None
    if affected == 0 and username is not None and current is None:
        return None
    return current


def delete(user_id):
    """계정을 지운다. 즐겨찾기·검색이력은 FK ON DELETE CASCADE로 함께 사라진다."""
    return db.execute_many("DELETE FROM users WHERE id = %s", [(user_id,)])
