from flask import Blueprint, jsonify, request

from app.services.manana import MananaError
from app.services.search_service import SearchError, search

bp = Blueprint("search", __name__, url_prefix="/api")


@bp.get("/search")
def search_songs():

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
