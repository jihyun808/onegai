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


@bp.post("/register")
@rate_limit(limit=10, window=60 * 60)
def register():
    body = request.get_json(silent=True) or {}
    try:
        created = auth_service.register(body.get("username"), body.get("password"))
    except AuthError as exc:
        return _fail(exc)

    session.clear()
    session[SESSION_KEY] = created["id"]
    session.permanent = True
    return jsonify(created), 201


@bp.post("/login")
@rate_limit(limit=20, window=60)
def login():
    body = request.get_json(silent=True) or {}
    try:
        found = auth_service.login(body.get("username"), body.get("password"))
    except AuthError as exc:
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
    user_id = session.get(SESSION_KEY)
    if not user_id:
        return jsonify(None)

    found = user.get(user_id)
    if found is None:
        session.clear()
        return jsonify(None)

    return jsonify(found)


@bp.patch("/me")
@rate_limit(limit=20, window=60)
@login_required
def update_me():
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


@bp.delete("/me")
@login_required
def delete_me():

    user.delete(session[SESSION_KEY])
    session.clear()
    return jsonify({"ok": True})
