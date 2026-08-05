"""회원가입 · 로그인 · 내 정보.

세션은 Flask의 서명 쿠키를 쓴다. httpOnly라 자바스크립트가 읽을 수 없어
XSS로 토큰이 새는 경로가 막힌다(SESSION_COOKIE_* 설정 참고).

실패 응답은 어느 입력이 문제인지 `field`로 알려준다.
클라이언트가 해당 입력창 아래에 메시지를 붙일 수 있게 하기 위함이다.
"""

from functools import wraps

from flask import Blueprint, jsonify, request, session

from app.models import user
from app.services import auth_service
from app.services.auth_service import AuthError
from app.utils.ratelimit import rate_limit

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

SESSION_KEY = "user_id"


def _fail(error, status=400):
    body = {"error": "invalid_request", "message": str(error)}
    if getattr(error, "field", None):
        body["field"] = error.field
    return jsonify(body), status


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if SESSION_KEY not in session:
            return jsonify({"error": "unauthorized", "message": "로그인이 필요해요."}), 401
        return view(*args, **kwargs)

    return wrapper


# 가입은 자주 할 일이 아니다. 한 곳에서 계정을 무더기로 만드는 것을 막는다.
@bp.post("/register")
@rate_limit(limit=10, window=60 * 60)
def register():
    """POST /api/auth/register {username, password}"""
    body = request.get_json(silent=True) or {}
    try:
        created = auth_service.register(body.get("username"), body.get("password"))
    except AuthError as exc:
        return _fail(exc)

    session.clear()
    session[SESSION_KEY] = created["id"]
    session.permanent = True
    return jsonify(created), 201


# 계정당 5회 제한과 별개다. 아이디를 바꿔가며 시도하면 그쪽 카운터는 안 오른다.
@bp.post("/login")
@rate_limit(limit=20, window=60)
def login():
    """POST /api/auth/login {username, password}"""
    body = request.get_json(silent=True) or {}
    try:
        found = auth_service.login(body.get("username"), body.get("password"))
    except AuthError as exc:
        # 인증 실패는 401이지만, 입력 형식 문제는 400으로 남긴다
        status = 401 if exc.field == "password" else 400
        return _fail(exc, status)

    session.clear()
    session[SESSION_KEY] = found["id"]
    session.permanent = True
    return jsonify(found)


@bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@bp.get("/me")
def me():
    """로그인 상태 확인. 안 했으면 null을 준다(401이 아니다)."""
    user_id = session.get(SESSION_KEY)
    if not user_id:
        return jsonify(None)

    found = user.get(user_id)
    if found is None:
        # 계정이 지워졌는데 쿠키만 남은 경우
        session.clear()
        return jsonify(None)

    return jsonify(found)


@bp.patch("/me")
@rate_limit(limit=20, window=60)
@login_required
def update_me():
    """PATCH /api/auth/me {username?, avatar?}"""
    body = request.get_json(silent=True) or {}
    try:
        updated = auth_service.update_profile(
            session[SESSION_KEY],
            username=body.get("username"),
            avatar=body.get("avatar"),
        )
    except AuthError as exc:
        return _fail(exc)

    return jsonify(updated)
