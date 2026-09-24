from flask import Blueprint, jsonify, request

from app.services import health_service, lyrics, translate
from app.models import song
from app.utils import cache, db

bp = Blueprint("health", __name__, url_prefix="/api")


@bp.get("/health")
def health():
    """서버 상태. ?deep=1 을 붙이면 외부 소스까지 실제로 찔러본다."""
    payload = {
        "status": "ok",
        "redis": cache.is_alive(),
        "mysql": db.is_alive(),
        # 클라이언트가 UI를 미리 감출 수 있도록 부가 기능 사용 가능 여부를 알린다
        "features": {
            "translate": translate.is_enabled(),
            "lyrics": lyrics.is_enabled(),
            "preview": True,  # iTunes Search는 키가 필요 없다
        },
    }

    if request.args.get("deep") in ("1", "true"):
        # 카탈로그가 얼마나 쌓였는지 — 크롤링 진행 상황 확인용
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
        # 금영 공식이 깨져도 manana 폴백이 살아 있으면 서비스는 돌아간다.
        # manana까지 죽어야 진짜 장애다.
        if not manana_ok:
            payload["status"] = "degraded"
        elif not kysing_ok:
            payload["status"] = "partial"

    return jsonify(payload)
