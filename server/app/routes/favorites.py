from flask import Blueprint, jsonify, request, session

from app.models import favorite
from app.routes.auth import SESSION_KEY, login_required
from app.services.search_service import _build_groups
from app.utils.normalize import normalize_entries
from app.utils.ratelimit import rate_limit

bp = Blueprint("favorites", __name__, url_prefix="/api/favorites")

MAX_BULK = 200


def _unavailable():
    return (
        jsonify({"error": "unavailable", "message": "즐겨찾기를 불러오지 못했어요."}),
        503,
    )


@bp.get("")
@login_required
def list_favorites():
    rows = favorite.list_for(session[SESSION_KEY])
    if rows is None:
        return _unavailable()

    items = normalize_entries(rows)
    return jsonify({"total": len(rows), "groups": _build_groups(items)})


@bp.post("")
@rate_limit(limit=60, window=60)
@login_required
def add_favorites():

    body = request.get_json(silent=True) or {}
    songs = body.get("songs")
    if not isinstance(songs, list) or not songs:
        return (
            jsonify({"error": "invalid_request", "message": "담을 곡이 없어요."}),
            400,
        )

    saved = favorite.add_many(session[SESSION_KEY], songs[:MAX_BULK])
    return jsonify({"saved": saved}), 201


@bp.delete("")
@login_required
def clear_favorites():
    favorite.clear(session[SESSION_KEY])
    return jsonify({"ok": True})


@bp.delete("/<brand>/<song_no>")
@login_required
def remove_favorite(brand, song_no):
    favorite.remove(session[SESSION_KEY], brand, song_no)
    return jsonify({"ok": True})
