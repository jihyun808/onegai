from flask import Blueprint, jsonify, request

from app.services.manana import MananaError
from app.services.search_service import SearchError, search

bp = Blueprint("search", __name__, url_prefix="/api")


@bp.get("/search")
def search_songs():
    """GET /api/search?q={검색어}&type={song|singer|lyrics}&brand={tj|kumyoung|all}

    full=1을 붙이면 공식 사이트까지 뒤진다(느림). 생략하면 자체 DB만 본다(빠름).
    응답의 complete가 false면 아직 전부가 아니라는 뜻이다.
    """
    try:
        payload = search(
            keyword=request.args.get("q"),
            search_type=request.args.get("type", "song"),
            brand=request.args.get("brand", "all"),
            limit=request.args.get("limit"),
            offset=request.args.get("offset"),
            full=request.args.get("full") in ("1", "true"),
            sort=request.args.get("sort", "release"),
            include_korean=request.args.get("korean") in ("1", "true"),
        )
    except SearchError as exc:
        return jsonify({"error": "invalid_request", "message": str(exc)}), 400
    except MananaError as exc:
        return jsonify({"error": "upstream_error", "message": str(exc)}), 502

    return jsonify(payload)

