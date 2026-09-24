import logging

from app.utils import db
from app.utils.normalize import normalize_text

logger = logging.getLogger(__name__)

_FIND = "SELECT singer FROM singer_alias WHERE alias_norm = %s"

_REMEMBER = """
    INSERT INTO singer_alias (alias_norm, singer)
    VALUES (%s, %s)
    ON DUPLICATE KEY UPDATE singer = VALUES(singer), hits = hits + 1
"""


def find(keyword):
    key = normalize_text(keyword)
    if not key:
        return None

    rows = db.query(_FIND, (key,))
    if not rows:
        return None

    return rows[0]["singer"]


def remember(keyword, singer):

    key = normalize_text(keyword)
    singer = (singer or "").strip()
    if not key or not singer:
        return False

    if key == normalize_text(singer):
        return False

    saved = db.execute_many(_REMEMBER, [(key, singer)])
    if saved:
        logger.info("가수 별칭을 배웠습니다: %r → %r", keyword, singer)

    return bool(saved)
