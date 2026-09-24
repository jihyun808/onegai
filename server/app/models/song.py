import logging

from app.utils import db
from app.utils.normalize import make_match_key, normalize_text

logger = logging.getLogger(__name__)

CHUNK = 500

_UPSERT = """
INSERT INTO songs
    (brand, no, title, singer, composer, lyricist, `release`,
     match_key, title_norm, singer_norm, source)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    title = VALUES(title),
    singer = VALUES(singer),
    composer = VALUES(composer),
    lyricist = VALUES(lyricist),
    -- 발매일은 덮어쓰지 않는다. 소스에 따라 비어 있을 수 있어서
    -- 이미 채워진 값을 빈 값으로 지우면 정렬이 망가진다.
    `release` = COALESCE(VALUES(`release`), `release`),
    match_key = VALUES(match_key),
    title_norm = VALUES(title_norm),
    singer_norm = VALUES(singer_norm),
    -- title_ko는 건드리지 않는다. 크롤은 원어만 가져오고 번역은 따로 채운다
    -- (translate-titles). 여기서 덮으면 크롤 한 번에 번역이 통째로 날아간다.
    source = VALUES(source)
"""


def _to_row(entry, source):
    title = entry.get("title") or ""
    singer = entry.get("singer") or ""
    release = entry.get("release") or None

    return (
        entry.get("brand") or "",
        entry.get("no") or "",
        title[:255],
        singer[:255],
        (entry.get("composer") or "")[:255],
        (entry.get("lyricist") or "")[:255],
        release,
        make_match_key(title, singer)[:512],
        normalize_text(title)[:255],
        normalize_text(singer)[:255],
        source,
    )


def upsert(entries, source):
    rows = [_to_row(e, source) for e in entries if e.get("no")]
    total = 0

    for start in range(0, len(rows), CHUNK):
        total += db.execute_many(_UPSERT, rows[start : start + CHUNK])

    return total


def _as_entry(row):
    release = row.get("release")
    return {
        "brand": row["brand"],
        "no": row["no"],
        "title": row["title"],
        "singer": row["singer"],
        "composer": row["composer"],
        "lyricist": row["lyricist"],
        "release": release.isoformat() if release else "",
        "title_ko": row.get("title_ko") or "",
    }


def search(keyword, search_type, brands, limit=500):

    if not brands:
        return []

    needle = normalize_text(keyword)
    if not needle:
        return []

    placeholders = ", ".join(["%s"] * len(brands))

    if search_type == "singer":
        where = "singer_norm LIKE %s"
        params = (*brands, f"%{needle}%", limit)
    else:
        where = "(title_norm LIKE %s OR title_ko_norm LIKE %s)"
        params = (*brands, f"%{needle}%", f"%{needle}%", limit)

    rows = db.query(
        f"""
        SELECT brand, no, title, title_ko, singer, composer, lyricist, `release`
        FROM songs
        WHERE brand IN ({placeholders}) AND {where}
        ORDER BY `release` DESC, no DESC
        LIMIT %s
        """,
        params,
    )

    if rows is None:
        return None

    return [_as_entry(row) for row in rows]


def count(brand=None):
    if brand:
        rows = db.query("SELECT COUNT(*) AS n FROM songs WHERE brand = %s", (brand,))
    else:
        rows = db.query("SELECT COUNT(*) AS n FROM songs")

    if rows is None:
        return None
    return rows[0]["n"]


def newest_release(brand):
    rows = db.query(
        "SELECT MAX(`release`) AS newest FROM songs WHERE brand = %s", (brand,)
    )
    if not rows or rows[0]["newest"] is None:
        return None
    return rows[0]["newest"].isoformat()


_UNTRANSLATED = """
    SELECT DISTINCT title
    FROM songs
    WHERE title_ko IS NULL
      AND title REGEXP '[ぁ-んァ-ヶ一-龥]'
    LIMIT %s
"""

_SET_TITLE_KO = """
    UPDATE songs SET title_ko = %s, title_ko_norm = %s WHERE title = %s
"""


def untranslated_titles(limit=200):

    rows = db.query(_UNTRANSLATED, (limit,))
    return [r["title"] for r in rows] if rows else []


def save_translations(pairs):
    rows = [
        (ko[:255], normalize_text(ko)[:255], title)
        for title, ko in pairs
        if title and ko
    ]
    return db.execute_many(_SET_TITLE_KO, rows) if rows else 0


def translation_progress():
    rows = db.query(
        """
        SELECT
            SUM(title_ko IS NOT NULL) AS done,
            SUM(title_ko IS NULL AND title REGEXP '[ぁ-んァ-ヶ一-龥]') AS todo
        FROM songs
        """
    )
    if not rows:
        return None
    return int(rows[0]["done"] or 0), int(rows[0]["todo"] or 0)
