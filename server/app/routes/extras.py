from flask import Blueprint, jsonify, request

from app.services import lyrics, preview, translate

bp = Blueprint("extras", __name__, url_prefix="/api")


@bp.get("/translate")
def translate_text():
    return jsonify(
        translate.translate(
            request.args.get("text", ""),
            target_lang=request.args.get("target", "KO").upper(),
        )
    )


@bp.get("/preview")
def song_preview():
    return jsonify(
        preview.find(request.args.get("title", ""), request.args.get("singer", ""))
    )


@bp.get("/lyrics")
def song_lyrics():
    return jsonify(
        lyrics.find(request.args.get("title", ""), request.args.get("singer", ""))
    )
