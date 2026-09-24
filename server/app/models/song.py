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
        # 번역 제목. 공식에서 온 결과에는 없으므로 빈 문자열이 기본이다.
        "title_ko": row.get("title_ko") or "",
    }


def search(keyword, search_type, brands, limit=500):
    """DB에서 검색한다. DB를 못 쓰면 None (빈 결과와 구분해야 한다).

    정규화한 검색어로 부분 일치를 본다. 그래서 공백·괄호·대소문자·
    카타카나 차이를 넘어 찾는다 — 외부 사이트가 못 하는 것이다.
    """
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
        # 곡명은 원어와 번역 제목을 함께 본다.
        # `만찬가`로 `晩餐歌`를 찾는 길이다 (11번, db/005_title_ko.sql).
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
    """아직 번역이 없는 제목. 같은 제목은 한 번만 옮기면 된다.

    가나·한자가 없는 제목(로마자·숫자)은 번역할 것이 없어 건너뛴다.
    """
    rows = db.query(_UNTRANSLATED, (limit,))
    return [r["title"] for r in rows] if rows else []


def save_translations(pairs):
    """[(원어 제목, 한국어 제목)]을 반영한다. 반영된 행 수."""
    rows = [
        (ko[:255], normalize_text(ko)[:255], title)
        for title, ko in pairs
        if title and ko
    ]
    return db.execute_many(_SET_TITLE_KO, rows) if rows else 0


def translation_progress():
    """번역 진행 상황 (번역됨, 남음)."""
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
