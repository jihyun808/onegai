import logging
import re

import bcrypt
from flask import current_app

from app.models import user
from app.utils import cache

logger = logging.getLogger(__name__)

USERNAME_MIN = 5
USERNAME_MAX = 20
PASSWORD_MIN = 8
PASSWORD_MAX = 72

_USERNAME = re.compile(r"^[A-Za-z0-9_]+$")

MAX_ATTEMPTS = 5
LOCK_SECONDS = 15 * 60


class AuthError(Exception):

    def __init__(self, message, field=None):
        super().__init__(message)
        self.field = field


def _attempt_key(username):
    return cache.make_key("login-fail", username.lower())


def _validate_username(username):
    username = (username or "").strip()
    if not (USERNAME_MIN <= len(username) <= USERNAME_MAX):
        raise AuthError(
            f"아이디는 {USERNAME_MIN}~{USERNAME_MAX}자로 입력해 주세요.", "username"
        )
    if not _USERNAME.match(username):
        raise AuthError("아이디는 영문, 숫자, 밑줄만 쓸 수 있어요.", "username")
    return username


def _validate_password(password):
    password = password or ""
    if len(password) < PASSWORD_MIN:
        raise AuthError(f"비밀번호는 {PASSWORD_MIN}자 이상으로 입력해 주세요.", "password")
    if len(password.encode("utf-8")) > PASSWORD_MAX:
        raise AuthError("비밀번호가 너무 길어요.", "password")
    return password


def hash_password(password):
    rounds = current_app.config["BCRYPT_ROUNDS"]
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds)).decode()


def verify_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode())
    except ValueError:
        return False


def register(username, password):
    username = _validate_username(username)
    password = _validate_password(password)

    taken = user.exists(username)
    if taken is None:
        raise AuthError("지금은 가입할 수 없어요. 잠시 후 다시 시도해 주세요.")
    if taken:
        raise AuthError("중복된 아이디예요.", "username")

    created = user.create(username, hash_password(password))
    if created is None:
        raise AuthError("중복된 아이디예요.", "username")

    return created


def attempts_left(username):
    used = cache.get_json(_attempt_key(username)) or 0
    return max(0, MAX_ATTEMPTS - used)


def _record_failure(username):
    key = _attempt_key(username)
    used = (cache.get_json(key) or 0) + 1
    cache.set_json(key, used, ttl=LOCK_SECONDS)
    return used


def login(username, password):
    username = _validate_username(username)

    if attempts_left(username) <= 0:
        raise AuthError(
            f"비밀번호를 {MAX_ATTEMPTS}번 틀렸어요. "
            f"{LOCK_SECONDS // 60}분 뒤에 다시 시도해 주세요.",
            "password",
        )

    found = user.find_by_username(username)
    if found is False:
        raise AuthError("지금은 로그인할 수 없어요. 잠시 후 다시 시도해 주세요.")

    if found is None or not verify_password(password, found["password_hash"]):
        if found is not None:
            used = _record_failure(username)
            left = MAX_ATTEMPTS - used
            if left <= 0:
                raise AuthError(
                    f"비밀번호를 {MAX_ATTEMPTS}번 틀렸어요. "
                    f"{LOCK_SECONDS // 60}분 뒤에 다시 시도해 주세요.",
                    "password",
                )
            raise AuthError(
                f"아이디 또는 비밀번호가 맞지 않아요. ({left}번 남음)", "password"
            )
        raise AuthError("아이디 또는 비밀번호가 맞지 않아요.", "password")

    cache.delete(_attempt_key(username))
    return {"id": found["id"], "username": found["username"], "avatar": found.get("avatar")}


def update_profile(user_id, username=None, avatar=None):
    if username is not None:
        username = _validate_username(username)

    if avatar:
        limit = current_app.config["AVATAR_MAX_BYTES"]
        if not avatar.startswith("data:image/"):
            raise AuthError("이미지 형식이 올바르지 않아요.", "avatar")
        if len(avatar) > limit:
            raise AuthError("이미지가 너무 커요.", "avatar")

    updated = user.update_profile(user_id, username=username, avatar=avatar)
    if updated is None:
        raise AuthError("중복된 아이디예요.", "username")
    return updated
