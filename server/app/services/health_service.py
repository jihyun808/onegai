import logging

from flask import current_app

from app.services import kysing, manana
from app.utils import cache

logger = logging.getLogger(__name__)

PROBE_KEYWORD = "ヨルシカ"
PROBE_TYPE = "singer"
PROBE_MIN_ROWS = 5

PROBE_CACHE_TTL = 300


def check_kysing():

    if not current_app.config["KYSING_ENABLED"]:
        return True, "disabled"

    key = cache.make_key("probe", "kysing")
    cached = cache.get_json(key)
    if cached is not None:
        return cached["ok"], cached["detail"]

    minimum = current_app.config.get("PROBE_MIN_ROWS", PROBE_MIN_ROWS)

    try:
        rows = kysing.search(PROBE_KEYWORD, search_type=PROBE_TYPE)
    except Exception as exc:
        ok, detail = False, f"error: {exc}"
    else:
        count = len(rows)
        has_fields = any(r.get("no") and r.get("title") for r in rows)
        if count >= minimum and has_fields:
            ok, detail = True, f"{count} rows"
        else:
            ok, detail = False, f"parser looks broken ({count} rows)"

    if not ok:
        logger.error("금영 공식 파서 점검 실패: %s", detail)

    cache.set_json(key, {"ok": ok, "detail": detail}, ttl=PROBE_CACHE_TTL)
    return ok, detail


def check_manana():
    key = cache.make_key("probe", "manana")
    cached = cache.get_json(key)
    if cached is not None:
        return cached["ok"], cached["detail"]

    minimum = current_app.config.get("PROBE_MIN_ROWS", PROBE_MIN_ROWS)

    try:
        rows = manana.search(PROBE_KEYWORD, search_type=PROBE_TYPE, brand="tj")
    except Exception as exc:
        ok, detail = False, f"error: {exc}"
    else:
        ok = len(rows) >= minimum
        detail = f"{len(rows)} rows"

    if not ok:
        logger.error("manana 점검 실패: %s", detail)

    cache.set_json(key, {"ok": ok, "detail": detail}, ttl=PROBE_CACHE_TTL)
    return ok, detail
