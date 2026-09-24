import logging
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from flask import current_app

from app.models import alias, song
from app.services import kysing, manana, tjmedia
from app.utils import cache
from app.utils.normalize import (
    normalize_entries,
    normalize_query,
    normalize_text,
    split_singers,
)

logger = logging.getLogger(__name__)

ALL_BRANDS = "all"

MAX_KEYWORD_LENGTH = 100

EMPTY_CACHE_TTL = 600

DEFAULT_LIMIT = 50
MAX_LIMIT = 200

SEARCH_TYPES = (*manana.SEARCH_TYPES, "lyrics")
LYRICS_TYPE = "lyrics"

_JAPANESE = re.compile(r"[ぁ-んァ-ヶ一-龥]")
_KOREAN = re.compile(r"[가-힣]")


def _is_korean_text(value):
    value = value or ""
    return bool(_KOREAN.search(value)) and not _JAPANESE.search(value)


def _is_korean_song(item):


    return _is_korean_text(item.get("title")) or _is_korean_text(item.get("singer"))


def _singer_matches(keyword, item):


    wanted = normalize_text(keyword)
    if not wanted:
        return True
    return any(normalize_text(part) == wanted for part in split_singers(item.get("singer")))


def _filter_singers(keyword, items):

    kept = [i for i in items if _singer_matches(keyword, i)]
    if not kept:
        logger.debug("가수 정확 일치가 없어 거르지 않습니다: %r", keyword)
        return items
    return kept

LYRICS_CROSS_LOOKUP_LIMIT = 15
SINGER_CROSS_LOOKUP_LIMIT = 1
LYRICS_LOOKUP_WORKERS = 6


class SearchError(Exception):
    pass


def _validate_brand(brand):
    brand = (brand or ALL_BRANDS).strip().lower()
    if brand != ALL_BRANDS and brand not in manana.SUPPORTED_BRANDS:
        allowed = ", ".join((*manana.SUPPORTED_BRANDS, ALL_BRANDS))
        raise SearchError(f"brand는 {allowed} 중 하나여야 합니다.")
    return brand


def _validate_paging(limit, offset):
    def as_int(value, default, label):
        if value is None or value == "":
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            raise SearchError(f"{label}은(는) 숫자여야 합니다.") from None

    limit = as_int(limit, DEFAULT_LIMIT, "limit")
    offset = as_int(offset, 0, "offset")

    if limit < 1:
        raise SearchError("limit은 1 이상이어야 합니다.")
    if limit > MAX_LIMIT:
        raise SearchError(f"limit은 {MAX_LIMIT}을 넘을 수 없습니다.")
    if offset < 0:
        raise SearchError("offset은 0 이상이어야 합니다.")

    return limit, offset


def _validate(keyword, search_type, brand):
    keyword = (keyword or "").strip()
    if not keyword:
        raise SearchError("검색어(q)를 입력해 주세요.")
    if len(keyword) > MAX_KEYWORD_LENGTH:
        raise SearchError(f"검색어는 {MAX_KEYWORD_LENGTH}자를 넘을 수 없습니다.")

    search_type = (search_type or "song").strip().lower()
    if search_type not in SEARCH_TYPES:
        raise SearchError(f"type은 {' 또는 '.join(SEARCH_TYPES)} 중 하나여야 합니다.")

    return keyword, search_type, _validate_brand(brand)


def _cache_key(keyword, search_type, brand, include_korean=False):

    key = cache.make_key("q2", search_type, brand, normalize_query(keyword))
    return f"{key}:ko" if include_korean else key


def _target_brands(brand):
    return manana.SUPPORTED_BRANDS if brand == ALL_BRANDS else (brand,)


def _group_by_brand(items, brand):
    grouped = {b: [] for b in _target_brands(brand)}

    for item in items:
        grouped[item["brand"]].append(item)

    return grouped


SORT_RELEASE = "release"
SORT_NUMBER = "no"
SORT_OPTIONS = (SORT_RELEASE, SORT_NUMBER)


def _sort_key(item):
    return (item["release"] or "", item["no"] or "")


def _number_key(item):
    no = item["no"] or ""
    return (no.isdigit(), int(no) if no.isdigit() else 0, no)


_OFFICIAL = {
    "kumyoung": (kysing, "KYSING_ENABLED"),
    "tj": (tjmedia, "TJMEDIA_ENABLED"),
}


def _fetch_official(brand, keyword, search_type):
    entry = _OFFICIAL.get(brand)
    if entry is None:
        return None

    module, flag = entry
    if not current_app.config[flag]:
        return None

    try:
        rows = module.search(keyword, search_type=search_type)
    except Exception as exc:
        logger.warning("%s 공식 조회 실패, manana로 폴백합니다: %s", brand, exc)
        return None

    if not rows:
        logger.info("%s 공식 결과 0건, manana로 보강합니다: %r", brand, keyword)
        return None

    return rows


def _fill_release(rows, keyword, search_type, brand):

    if all(row.get("release") for row in rows):
        return rows

    try:
        known = {
            item["no"]: item.get("release", "")
            for item in manana.search(keyword, search_type=search_type, brand=brand)
        }
    except Exception as exc:
        logger.info("발매일 보강 실패, 순서만 영향받습니다: %s", exc)
        return rows

    for row in rows:
        if not row.get("release"):
            row["release"] = known.get(row["no"], "")

    return rows


def _fetch_lyrics(keyword, brand):

    if not current_app.config["KYSING_ENABLED"]:
        raise SearchError("가사 검색을 지금은 쓸 수 없어요.")

    try:
        found = kysing.search(keyword, search_type=LYRICS_TYPE)
    except Exception as exc:
        logger.warning("가사 검색 실패: %s", exc)
        raise manana.MananaError("가사 검색에 실패했습니다.") from exc

    rows = [row for row in found if brand in ("kumyoung", ALL_BRANDS)]

    if brand == "kumyoung" or not found:
        return rows

    titles = [
        row["title"].strip()
        for row in found[:LYRICS_CROSS_LOOKUP_LIMIT]
        if row.get("title", "").strip()
    ]

    app = current_app._get_current_object()

    def lookup(title):
        with app.app_context():
            try:
                return _fetch_brand("tj", title, "song")
            except Exception as exc:
                logger.info("가사 검색 중 TJ 역조회 실패 (%r): %s", title, exc)
                return []

    with ThreadPoolExecutor(max_workers=LYRICS_LOOKUP_WORKERS) as pool:
        for found_rows in pool.map(lookup, titles):
            rows.extend(found_rows)

    return rows


def _search_by_alias(brand, keyword, search_type):


    if search_type != "singer" or _JAPANESE.search(keyword):
        return []

    canonical = alias.find(keyword)
    if not canonical:
        return []

    rows = song.search(canonical, "singer", _target_brands(brand))
    if not rows:
        return []

    logger.info("별칭으로 답합니다: %r → %r (%d건)", keyword, canonical, len(rows))
    return rows


def _fetch_official_all(brand, keyword, search_type):

    rows = _fetch_all_brands(brand, keyword, search_type)
    if search_type == "singer":
        rows = _cross_lookup_singers(rows, _target_brands(brand), keyword)
    return rows


def _cross_lookup_singers(rows, targets, keyword):


    if _JAPANESE.search(keyword):
        return rows
    found = {t: [r for r in rows if r["brand"] == t] for t in targets}
    empty = [t for t, got in found.items() if not got]
    filled = [t for t, got in found.items() if got]

    if not empty or not filled:
        return rows

    asked = normalize_text(keyword)
    names = []
    for target in filled:
        for row in found[target]:
            for name in split_singers(row.get("singer")):
                if normalize_text(name) != asked and name not in names:
                    names.append(name)

    if not names:
        return rows

    counts = Counter(
        normalize_text(name)
        for target in filled
        for row in found[target]
        for name in split_singers(row.get("singer"))
    )
    names.sort(key=lambda n: counts[normalize_text(n)], reverse=True)
    names = names[:SINGER_CROSS_LOOKUP_LIMIT]

    app = current_app._get_current_object()

    def lookup(job):
        brand, name = job
        with app.app_context():
            try:
                return _fetch_brand(brand, name, "singer")
            except Exception as exc:
                logger.info("가수 역조회 실패 (%s / %r): %s", brand, name, exc)
                return []

    jobs = [(brand, name) for brand in empty for name in names]
    logger.info("%s가 0건이라 %r로 역조회합니다", ", ".join(empty), names)

    extra = []
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        for got in pool.map(lookup, jobs):
            extra.extend(got)

    gained = [r for r in extra if r["brand"] in empty]

    if gained:
        try:
            alias.remember(keyword, names[0])
        except Exception as exc:
            logger.info("별칭 저장 실패, 결과에는 영향 없습니다: %s", exc)

    return _merge(rows, gained)


def _fetch_brand(brand, keyword, search_type):


    rows = _fetch_official(brand, keyword, search_type)
    if rows is None:
        return manana.search(keyword, search_type=search_type, brand=brand)

    return _fill_release(rows, keyword, search_type, brand)


def _merge(primary, extra):
    seen = {(row["brand"], row["no"]) for row in primary}
    merged = list(primary)

    for row in extra:
        key = (row["brand"], row["no"])
        if key not in seen:
            seen.add(key)
            merged.append(row)

    return merged


def _fetch_catalog(brand, keyword, search_type, full=False):


    if not current_app.config["DB_SEARCH_ENABLED"]:
        return _fetch_official_all(brand, keyword, search_type), True

    rows = song.search(keyword, search_type, _target_brands(brand))

    if rows is None:
        return _fetch_official_all(brand, keyword, search_type), True

    if not full:
        learned = _search_by_alias(brand, keyword, search_type)
        if learned:
            return _merge(rows, learned), True

        needs_official = not rows or not _JAPANESE.search(keyword)
        return rows, not needs_official

    logger.info("DB %d건, 공식으로 보강합니다: %r", len(rows), keyword)
    try:
        return _merge(rows, _fetch_official_all(brand, keyword, search_type)), True
    except Exception as exc:
        logger.warning("공식 보강 실패, DB 결과만 씁니다: %s", exc)
        if rows:
            return rows, True
        raise


def _fetch_all_brands(brand, keyword, search_type):

    targets = _target_brands(brand)
    if len(targets) == 1:
        return _fetch_brand(targets[0], keyword, search_type)

    app = current_app._get_current_object()
    errors = []

    def fetch(target):
        with app.app_context():
            try:
                return _fetch_brand(target, keyword, search_type)
            except Exception as exc:
                errors.append(exc)
                logger.warning("%s 조회 실패: %s", target, exc)
                return []

    rows = []
    with ThreadPoolExecutor(max_workers=len(targets)) as pool:
        for found in pool.map(fetch, targets):
            rows.extend(found)

    if errors and len(errors) == len(targets):
        raise errors[0]

    return rows


def _build_groups(items):

    groups = {}

    for item in items:
        group = groups.get(item["match_key"])
        if group is None:
            group = {
                "title": item["title"],
                "title_ko": item.get("title_ko", ""),
                "singer": item["singer"],
                "match_key": item["match_key"],
                "brands": {},
            }
            groups[item["match_key"]] = group

        group["brands"].setdefault(item["brand"], []).append(item["no"])

        if not group["title_ko"] and item.get("title_ko"):
            group["title_ko"] = item["title_ko"]

    ordered = list(groups.values())
    for group in ordered:
        group["both"] = len(group["brands"]) > 1

    return ordered


def search(keyword, search_type="song", brand=ALL_BRANDS, limit=None, offset=None,
           full=False, sort=SORT_RELEASE, include_korean=False):
    keyword, search_type, brand = _validate(keyword, search_type, brand)
    limit, offset = _validate_paging(limit, offset)

    key = _cache_key(keyword, search_type, brand, include_korean)
    if not full:
        key += ":quick"
    cached = cache.get_json(key)

    if cached is not None:
        items = cached
        from_cache = True
        complete = full
    else:
        try:
            if search_type == LYRICS_TYPE:
                raw = _fetch_lyrics(keyword, brand)
                complete = True
            else:
                raw, complete = _fetch_catalog(brand, keyword, search_type, full)
        except manana.MananaError:
            stale = cache.get_stale(key)
            if stale is None:
                raise
            logger.warning("업스트림 전부 실패, 만료된 캐시로 응답합니다: %r", keyword)
            return _build_response(
                stale, brand, True, query=keyword, search_type=search_type,
                limit=limit, offset=offset, stale=True,
            )

        allowed = set(_target_brands(brand))
        items = [
            i
            for i in normalize_entries(raw)
            if i["brand"] in allowed
            and (include_korean or not _is_korean_song(i))
        ]
        if search_type == "singer":
            items = _filter_singers(keyword, items)

        items.sort(key=_sort_key, reverse=True)

        if items:
            cache.set_with_stale(key, items)
        else:
            cache.set_json(key, items, ttl=EMPTY_CACHE_TTL)
        from_cache = False

    if sort == SORT_NUMBER:
        items = sorted(items, key=_number_key, reverse=True)

    return _build_response(
        items,
        brand,
        from_cache,
        query=keyword,
        search_type=search_type,
        limit=limit,
        offset=offset,
        complete=complete,
    )


def _build_response(
    items, brand, from_cache, query=None, search_type=None, limit=None, offset=0,
    stale=False, complete=True,
):
    total = len(items)

    page = items if limit is None else items[offset : offset + limit]

    grouped = _group_by_brand(page, brand)
    groups = _build_groups(page)

    payload = {
        "brand": brand,
        "cached": from_cache,
        "total": total,
        "songs": len(_build_groups(items)),
        "counts": {b: len(v) for b, v in grouped.items()},
        "matched": sum(1 for g in groups if g["both"]),
        "results": grouped,
        "groups": groups,
    }

    if limit is not None:
        payload["limit"] = limit
        payload["offset"] = offset
        payload["returned"] = len(page)
        payload["has_more"] = offset + len(page) < total

    payload["complete"] = complete

    if stale:
        payload["stale"] = True

    if query is not None:
        payload["query"] = query
    if search_type is not None:
        payload["type"] = search_type

    return payload
