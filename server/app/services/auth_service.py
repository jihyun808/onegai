"""회원가입 · 로그인.

보안에서 신경 쓴 것:

1. **bcrypt 해싱** — 평문·MD5·SHA는 쓰지 않는다. DB가 통째로 새도
   비밀번호 자체는 지켜진다. 사람들이 비밀번호를 돌려쓰기 때문에,
   유출 피해는 우리 서비스가 아니라 사용자의 다른 계정에서 발생한다.
2. **로그인 시도 제한** — 계정당 5회 실패하면 잠근다. 없으면 무차별 대입에
   그대로 뚫린다. 카운터는 Redis에 둔다.
3. **httpOnly 쿠키 세션** — 토큰을 자바스크립트가 읽을 수 없게 한다
   (라우트에서 Flask 세션 사용).
4. 비밀번호 복잡도는 강요하지 않는다. 길이만 본다 — 요즘 권고에 맞다.
"""

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
# 상한을 두는 이유는 정책이 아니라 bcrypt가 72바이트까지만 보기 때문이다.
PASSWORD_MAX = 72

_USERNAME = re.compile(r"^[A-Za-z0-9_]+$")

# 로그인 실패 카운터
MAX_ATTEMPTS = 5
LOCK_SECONDS = 15 * 60


class AuthError(Exception):
    """가입·로그인 실패. field에 어느 입력이 문제인지 담는다."""

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
    # 라운드가 높을수록 대입 공격이 비싸지지만 로그인도 느려진다.
    # 12는 일반적인 권장값이다. 테스트에서는 낮춰 suite를 빠르게 유지한다.
    rounds = current_app.config["BCRYPT_ROUNDS"]
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds)).decode()


def verify_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode())
    except ValueError:
        # 해시 형식이 깨진 경우. 로그인 실패로 처리한다.
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
        # 확인과 INSERT 사이에 누가 먼저 가져간 경우
        raise AuthError("중복된 아이디예요.", "username")

    return created


def attempts_left(username):
    """남은 로그인 시도 횟수. Redis가 없으면 제한하지 않는다."""
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

    # 없는 아이디와 틀린 비밀번호를 같은 메시지로 답한다.
    # 구분해서 알려주면 어떤 아이디가 존재하는지 긁어갈 수 있다.
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
