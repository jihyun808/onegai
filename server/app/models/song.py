"""songs 테이블 조회/적재.

검색 결과는 manana와 같은 스키마로 돌려준다. 그래야 상위 계층이
DB에서 왔는지 외부에서 왔는지 신경 쓰지 않아도 된다.
"""

import logging

from app.utils import db
from app.utils.normalize import make_match_key, normalize_text

logger = logging.getLogger(__name__)

# 한 번에 밀어 넣는 행 수
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
    """곡들을 저장한다. 이미 있으면 갱신한다. 반영된 행 수를 돌려준다."""
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
    }


def search(keyword, search_type, brands, limit=500):
    """DB에서 검색한다. DB를 못 쓰면 None (빈 결과와 구분해야 한다).

    정규화한 검색어로 부분 일치를 본다. 그래서 공백·괄호·대소문자·
    카타카나 차이를 넘어 찾는다 — 외부 사이트가 못 하는 것이다.
    """
    if not brands:
        return []

    column = "singer_norm" if search_type == "singer" else "title_norm"
    needle = normalize_text(keyword)
    if not needle:
        return []

    placeholders = ", ".join(["%s"] * len(brands))
    rows = db.query(
        f"""
        SELECT brand, no, title, singer, composer, lyricist, `release`
        FROM songs
        WHERE brand IN ({placeholders}) AND {column} LIKE %s
        ORDER BY `release` DESC, no DESC
        LIMIT %s
        """,
        (*brands, f"%{needle}%", limit),
    )

    if rows is None:
        return None

    return [_as_entry(row) for row in rows]


def count(brand=None):
    """적재된 곡 수. DB를 못 쓰면 None."""
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
