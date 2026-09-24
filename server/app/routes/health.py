from flask import Blueprint, jsonify, request

from app.services import health_service, lyrics, translate
from app.models import song
from app.utils import cache, db

bp = Blueprint("health", __name__, url_prefix="/api")


@bp.get("/health")
def health():
    payload = {
        "status": "ok",
        "redis": cache.is_alive(),
        "mysql": db.is_alive(),
        "features": {
            "translate": translate.is_enabled(),
            "lyrics": lyrics.is_enabled(),
            "preview": True,
        },
    }

    if request.args.get("deep") in ("1", "true"):
        payload["catalog"] = {
            brand: {"songs": song.count(brand), "newest": song.newest_release(brand)}
            for brand in ("tj", "kumyoung")
        }

        kysing_ok, kysing_detail = health_service.check_kysing()
        manana_ok, manana_detail = health_service.check_manana()

        payload["sources"] = {
            "kysing": {"ok": kysing_ok, "detail": kysing_detail},
            "manana": {"ok": manana_ok, "detail": manana_detail},
        }
        if not manana_ok:
            payload["status"] = "degraded"
        elif not kysing_ok:
            payload["status"] = "partial"

    return jsonify(payload)
