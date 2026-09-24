"""번역 · 미리듣기 · 가사.

검색을 거들기만 하는 부가 기능이라, 키가 없거나 외부 API가 죽어도
에러를 내지 않는다. 항상 200과 함께 available 플래그를 돌려주므로
클라이언트는 해당 영역만 감추면 된다.
"""

from flask import Blueprint, jsonify, request

from app.services import lyrics, preview, translate

bp = Blueprint("extras", __name__, url_prefix="/api")


@bp.get("/translate")
def translate_text():
    """GET /api/translate?text={일본어}&target={KO}"""
    return jsonify(
        translate.translate(
            request.args.get("text", ""),
            target_lang=request.args.get("target", "KO").upper(),
        )
    )


@bp.get("/preview")
def song_preview():
    """GET /api/preview?title={}&singer={}"""
    return jsonify(
        preview.find(request.args.get("title", ""), request.args.get("singer", ""))
    )


@bp.get("/lyrics")
def song_lyrics():
    """GET /api/lyrics?title={}&singer={}"""
    return jsonify(
        lyrics.find(request.args.get("title", ""), request.args.get("singer", ""))
    )
