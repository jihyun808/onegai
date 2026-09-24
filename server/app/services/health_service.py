"""외부 소스 상태 점검.

금영 공식 사이트는 공개 API가 아니라 HTML 파싱이다. 사이트 구조가 바뀌면
예외 없이 **조용히 0건**을 반환하기 때문에, 사용자 신고 전에는 알 방법이 없다.
그래서 결과가 있어야 마땅한 검색어를 정기적으로 던져 확인한다.
"""

import logging

from flask import current_app

from app.services import kysing, manana
from app.utils import cache

logger = logging.getLogger(__name__)

# 파서 점검용 표본.
# 곡 수가 많고 오래된 가수라 데이터가 사라질 가능성이 낮다.
# 최소 기대치는 넉넉히 잡아, 몇 곡 빠진 정도로는 경보가 울리지 않게 한다.
PROBE_KEYWORD = "ヨルシカ"
PROBE_TYPE = "singer"
PROBE_MIN_ROWS = 5  # 기본값. app.config["PROBE_MIN_ROWS"]로 덮을 수 있다

# 점검 결과 캐시. 헬스체크 때문에 매번 외부를 치지 않게 한다.
PROBE_CACHE_TTL = 300


def check_kysing():
    """금영 공식 파서가 살아있는지 확인한다.

    반환: (ok, detail)
    """
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
        # 행은 나왔는데 곡번호가 비었다면 마크업이 바뀐 것이다
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
