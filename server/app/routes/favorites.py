"""즐겨찾기.

화면은 곡 단위(그룹)로 다루지만 저장은 브랜드별 번호 단위다.
그래서 목록을 내보낼 때 검색과 같은 방식으로 다시 묶어 준다 —
클라이언트가 SongCard를 그대로 재사용할 수 있다.
"""

from flask import Blueprint, jsonify, request, session

from app.models import favorite
from app.routes.auth import SESSION_KEY, login_required
from app.services.search_service import _build_groups
from app.utils.normalize import normalize_entries
from app.utils.ratelimit import rate_limit

bp = Blueprint("favorites", __name__, url_prefix="/api/favorites")

# 로컬에 쌓인 것을 한 번에 올릴 때를 대비한 상한
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

    # 검색과 같은 정규화·그룹핑을 거쳐 곡 단위로 묶는다
    items = normalize_entries(rows)
    return jsonify({"total": len(rows), "groups": _build_groups(items)})


@bp.post("")
@rate_limit(limit=60, window=60)
@login_required
def add_favorites():
    """POST /api/favorites {songs: [{brand, no, title, singer}, ...]}

    한 곡만 담을 때도, 로그인 직후 로컬 목록을 통째로 올릴 때도 같은 형태를 쓴다.
    """
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
    """담아둔 곡을 전부 지운다."""
    favorite.clear(session[SESSION_KEY])
    return jsonify({"ok": True})


@bp.delete("/<brand>/<song_no>")
@login_required
def remove_favorite(brand, song_no):
    favorite.remove(session[SESSION_KEY], brand, song_no)
    return jsonify({"ok": True})
