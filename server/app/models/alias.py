"""검색어 → 가수 원표기 별칭 (db/004_singer_alias.sql).

발음 검색('미쿠')을 자체 DB가 답할 수 있게 만드는 다리다.
공식에 한 번 물어서 알아낸 원표기('初音ミク')를 적어 두고, 다음부터는
공식을 부르지 않는다. **남의 서버를 덜 치는 것이 목적이다.**
"""

import logging

from app.utils import db
from app.utils.normalize import normalize_text

logger = logging.getLogger(__name__)

_FIND = "SELECT singer FROM singer_alias WHERE alias_norm = %s"

# 같은 별칭을 다시 배우면 횟수만 올린다.
# 원표기가 달라졌을 때만 덮어쓴다 — 공식이 표기를 바꾸는 일이 있다.
_REMEMBER = """
    INSERT INTO singer_alias (alias_norm, singer)
    VALUES (%s, %s)
    ON DUPLICATE KEY UPDATE singer = VALUES(singer), hits = hits + 1
"""


def find(keyword):
    """검색어에 해당하는 가수 원표기. 없거나 DB를 못 쓰면 None."""
    key = normalize_text(keyword)
    if not key:
        return None

    rows = db.query(_FIND, (key,))
    if not rows:
        return None

    return rows[0]["singer"]


def remember(keyword, singer):
    """공식이 알려준 연결을 저장한다. 실패해도 조용히 넘어간다.

    검색 흐름 한가운데서 부르므로 **여기서 예외가 나면 안 된다.**
    저장에 실패하면 다음 검색이 느릴 뿐 결과는 같다.
    """
    key = normalize_text(keyword)
    singer = (singer or "").strip()
    if not key or not singer:
        return False

    # 이미 같은 표기로 찾을 수 있으면 적어 둘 이유가 없다
    if key == normalize_text(singer):
        return False

    saved = db.execute_many(_REMEMBER, [(key, singer)])
    if saved:
        logger.info("가수 별칭을 배웠습니다: %r → %r", keyword, singer)

    return bool(saved)
