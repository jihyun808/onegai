"""검색 서비스: manana 호출 → 정규화 → 브랜드별 그룹핑, Redis 캐싱."""

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

# 캐시 키가 무한정 길어지지 않도록 검색어 길이를 제한한다.
MAX_KEYWORD_LENGTH = 100

# 결과 없음은 짧게만 캐싱한다.
# 업스트림 일시 오류나 오타 검색이 24시간 동안 굳는 것을 막는다.
EMPTY_CACHE_TTL = 600

# 페이지네이션.
# 넓은 검색어는 결과가 2만 건을 넘는다 (q=a → 24,162건 / 13.7MB).
# 모바일에서 통째로 내려받을 수 없으므로 페이지 단위로 자른다.
DEFAULT_LIMIT = 50
MAX_LIMIT = 200

# 가사 검색은 금영 공식에만 있다. TJ 공식·manana 모두 지원하지 않는다.
# 그래서 금영에서 곡을 찾은 뒤, 그 제목으로 TJ 번호를 역조회해 붙인다.
SEARCH_TYPES = (*manana.SEARCH_TYPES, "lyrics")
LYRICS_TYPE = "lyrics"

# 일본어(가나·한자)가 들어간 검색어. 자체 DB가 답할 수 있는 종류다.
# 한글 발음('요루시카')이나 로마자('kakeru')는 공식 검색 인덱스에만 있어
# 크롤링으로 가져올 수 없다 — 그럴 때만 공식을 찌른다.
_JAPANESE = re.compile(r"[ぁ-んァ-ヶ一-龥]")
_KOREAN = re.compile(r"[가-힣]")


def _is_korean_text(value):
    """한글이 있고 일본어(가나·한자)가 전혀 없는 표기인지."""
    value = value or ""
    return bool(_KOREAN.search(value)) and not _JAPANESE.search(value)


def _is_korean_song(item):
    """일본곡 앱에 섞여 들어온 한국곡인지.

    '미쿠'로 검색하면 드라마 '미미쿠스' OST 같은 한국곡이 딸려 온다.
    노래방 DB가 부분 문자열로 매칭하기 때문이다.

    **제목과 가수를 각각 본다.** 붙여서 한 덩어리로 보면 둘 중 하나만
    일본어여도 통과한다 — 제목이 일본어인 한국 가수 곡(아이유 '사쿠라'
    같은 커버·일본 활동곡)이 그렇게 새어 들어왔다.

    판정은 보수적이다. 한글이 있고 일본어가 전혀 없을 때만 한국어 표기로
    본다. 애니 주제가의 한국어 더빙판(예: 코요태 '우리의꿈(원피스 OP)')은
    실제로 한국곡이라 걸러도 무방하다.

    일본 가수를 한글로 등록한 곡이 함께 걸릴 수 있어 실측했다 —
    일본 가수 8팀을 한글 발음으로 조회한 결과 **0건**이었다 (23번 표).
    생기더라도 설정에서 '한국곡 포함'을 켜면 다시 보인다.
    """
    return _is_korean_text(item.get("title")) or _is_korean_text(item.get("singer"))


def _singer_matches(keyword, item):
    """가수 검색 결과가 정말 그 가수의 곡인지.

    노래방 DB는 가수명을 부분 문자열로 찾는다. 'Ado'를 검색하면
    'ADOY', 'ADORA', 'Owen Ovadoz'가 딸려 온다 (70건 중 36건, 2026-08-19).

    **이름을 통째로 비교하지 않고 쪼갠 뒤 비교한다.** 통째로 보면
    'Ado,初音ミク'나 '아이유,박보검' 같은 합작곡이 함께 사라진다.
    쪼개면 'ADOY'는 그대로 탈락하면서 합작곡은 살아남는다.
    """
    wanted = normalize_text(keyword)
    if not wanted:
        return True
    return any(normalize_text(part) == wanted for part in split_singers(item.get("singer")))


def _filter_singers(keyword, items):
    """가수 검색 결과에서 이름만 겹친 남을 걷어낸다.

    **하나도 안 남으면 거르기 전 결과를 그대로 쓴다.** 검색어가 이름의
    일부일 때가 있다 — '미쿠'로 '初音ミク'를 찾는 식이다. 그런 검색은
    정확 일치가 0건이라, 거르면 화면이 통째로 비어버린다.
    지금까지와 같은 결과를 주는 편이 아무것도 안 주는 것보다 낫다.
    """
    kept = [i for i in items if _singer_matches(keyword, i)]
    if not kept:
        logger.debug("가수 정확 일치가 없어 거르지 않습니다: %r", keyword)
        return items
    return kept

# 역조회는 곡마다 TJ를 한 번씩 부른다. 폭주를 막기 위해 상한을 둔다.
LYRICS_CROSS_LOOKUP_LIMIT = 15
# 가수 역조회에 쓸 이름 개수.
# 2로 늘려 봤더니 두 번째 이름이 피처링 아티스트라 그 사람 전곡이 딸려 왔고,
# `미쿠` 검색이 17초까지 늘어졌다. 가장 많이 나온 이름 하나면 충분하다.
SINGER_CROSS_LOOKUP_LIMIT = 1
# 순차로 돌면 40초가 걸린다. 남의 서버이므로 동시 요청은 적당히 제한한다.
LYRICS_LOOKUP_WORKERS = 6


class SearchError(Exception):
    """잘못된 검색 요청."""


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
    """표기 흔들림만 흡수한다. 공백/기호를 지우면 서로 다른 검색어가
    같은 키를 공유해 결과가 섞인다. normalize_query 주석 참고.

    정렬 기준은 키에 넣지 않는다 — 같은 결과를 다르게 늘어놓을 뿐이다.
    한국곡 포함 여부는 결과 자체가 달라지므로 넣는다.
    """
    # 'q'로 시작해 부가 기능 캐시와 이름 공간을 나눈다. 이게 없으면
    # `type=lyrics` 검색과 `/api/lyrics` 조회가 같은 키를 쓴다 —
    # `lyrics:all:yoasobi`가 "brand=all에서 yoasobi 가사 검색"이자
    # "ALL(곡)/YOASOBI의 가사"로 읽혀 서로의 응답을 덮어쓴다.
    # 'q2'의 2는 캐시 세대다. 가수 노이즈 필터(_filter_singers)가 들어가면서
    # 같은 검색어의 결과 내용이 달라졌다. 이름을 안 바꾸면 배포 후 24시간 동안
    # 거르기 전 결과가 캐시에서 그대로 나간다.
    key = cache.make_key("q2", search_type, brand, normalize_query(keyword))
    return f"{key}:ko" if include_korean else key


def _target_brands(brand):
    return manana.SUPPORTED_BRANDS if brand == ALL_BRANDS else (brand,)


def _group_by_brand(items, brand):
    """브랜드별로 나눈다. 요청 브랜드는 결과가 없어도 빈 배열로 노출한다."""
    grouped = {b: [] for b in _target_brands(brand)}

    for item in items:
        # 지원 대상 밖의 브랜드는 이미 걸러진 상태다.
        grouped[item["brand"]].append(item)

    return grouped


# 사용자가 고를 수 있는 정렬 기준
SORT_RELEASE = "release"
SORT_NUMBER = "no"
SORT_OPTIONS = (SORT_RELEASE, SORT_NUMBER)


def _sort_key(item):
    # 최신 발매순, 같은 날짜면 번호순
    return (item["release"] or "", item["no"] or "")


def _number_key(item):
    """곡번호순. 번호는 문자열이라 그냥 정렬하면 9가 10보다 뒤로 간다."""
    no = item["no"] or ""
    return (no.isdigit(), int(no) if no.isdigit() else 0, no)


# 브랜드별 공식 사이트 스크래퍼와, 켜고 끄는 설정 키
_OFFICIAL = {
    "kumyoung": (kysing, "KYSING_ENABLED"),
    "tj": (tjmedia, "TJMEDIA_ENABLED"),
}


def _fetch_official(brand, keyword, search_type):
    """공식 사이트에서 가져온다. 실패하거나 0건이면 None을 돌려준다."""
    entry = _OFFICIAL.get(brand)
    if entry is None:
        return None

    module, flag = entry
    if not current_app.config[flag]:
        return None

    try:
        rows = module.search(keyword, search_type=search_type)
    except Exception as exc:
        # 네트워크 실패든 마크업 변경으로 인한 파서 크래시든 똑같이 폴백한다
        logger.warning("%s 공식 조회 실패, manana로 폴백합니다: %s", brand, exc)
        return None

    if not rows:
        # 0건이 정상일 수도(없는 가수) 있지만 파서가 깨져도 0건이다.
        # 구분할 방법이 없으므로 manana로 보강한다.
        logger.info("%s 공식 결과 0건, manana로 보강합니다: %r", brand, keyword)
        return None

    return rows


def _fill_release(rows, keyword, search_type, brand):
    """발매일이 빠진 항목을 manana 데이터로 채운다.

    TJ 공식 검색 결과에는 발매일이 없다(금영 공식에는 출시월이 있다).
    그대로 두면 정렬 기준이 비어 TJ 결과가 통째로 목록 아래로 밀린다.
    manana는 TJ 발매일을 갖고 있으므로 곡번호로 맞춰 채운다.
    실패해도 그냥 넘어간다 — 순서가 조금 흔들릴 뿐 결과는 나온다.
    """
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
    """가사로 검색한다.

    가사 인덱스는 금영 공식에만 있다. 그래서 금영에서 곡을 찾고,
    찾은 제목으로 TJ를 다시 뒤져 번호를 붙인다. 우리 그룹핑이
    제목 정규화로 두 브랜드를 묶어 주므로 한 카드에 양쪽 번호가 나온다.
    """
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

    # 금영에서 찾은 곡의 제목으로 TJ 번호를 역조회한다.
    # 순차로 돌면 곡당 2~3초씩 쌓여 40초에 육박한다. 병렬로 부른다.
    app = current_app._get_current_object()

    def lookup(title):
        with app.app_context():
            try:
                return _fetch_brand("tj", title, "song")
            except Exception as exc:
                # 한 곡 실패가 전체를 막지 않게 한다
                logger.info("가사 검색 중 TJ 역조회 실패 (%r): %s", title, exc)
                return []

    with ThreadPoolExecutor(max_workers=LYRICS_LOOKUP_WORKERS) as pool:
        for found_rows in pool.map(lookup, titles):
            rows.extend(found_rows)

    return rows


def _search_by_alias(brand, keyword, search_type):
    """전에 배워 둔 원표기로 자체 DB를 뒤진다. 못 쓰면 빈 리스트.

    `미쿠`처럼 발음으로 검색하면 DB가 답하지 못한다 — DB에는 `初音ミク`로
    들어 있기 때문이다. 한 번 공식에 물어서 알아낸 연결(38번의 역조회)을
    `singer_alias`에 적어 두고, 그다음부터는 이 길로 답한다.

    **공식 호출이 사라지는 것이 요점이다.** 결과를 완전하다고 표시하므로
    클라이언트가 2차 요청도 보내지 않는다.
    """
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
    """공식 조회 + 가수 역조회. 공식을 훑는 경로는 모두 이걸 쓴다.

    역조회를 여기 둔 이유 — DB 장애로 공식만 보는 경로에서도 같은 보정이
    필요하다. 공식을 부르는 자리는 세 곳(DB 끔 / DB 장애 / 2차 보강)인데
    모두 여기를 지난다.
    """
    rows = _fetch_all_brands(brand, keyword, search_type)
    if search_type == "singer":
        rows = _cross_lookup_singers(rows, _target_brands(brand), keyword)
    return rows


def _cross_lookup_singers(rows, targets, keyword):
    """한쪽 브랜드가 0건일 때, 다른 쪽이 찾아 준 가수명으로 다시 물어본다.

    **왜 필요한가** — 발음 검색의 커버리지가 브랜드마다 다르다 (11번).
    `미쿠`로 조회하면 금영은 115건을 주는데 TJ는 0건이다. TJ는 이름 전체를
    쳐야(`하츠네미쿠`) 걸리기 때문이다. 그런데 금영이 돌려준 행에는
    **일본어 원표기(`初音ミク`)가 들어 있고**, 그걸로 TJ에 물으면 122건이 나온다.

    가사 검색(`_fetch_lyrics`)이 쓰는 역조회와 같은 수법이다. 다만 그쪽은
    곡마다 한 번씩 부르고, 여기는 **가수명 한두 개로 한 번씩만** 부른다.

    비어 있는 브랜드가 없거나 쓸 만한 이름이 없으면 아무것도 하지 않는다.
    실패해도 원래 결과를 그대로 돌려준다.

    **검색어에 일본어가 있으면 하지 않는다.** 그때 0건은 표기 문제가 아니라
    정말 그 브랜드에 없는 것이다. 굳이 다른 이름으로 다시 물으면 시간만
    쓰고 엉뚱한 곡을 끌어온다.
    """
    if _JAPANESE.search(keyword):
        return rows
    found = {t: [r for r in rows if r["brand"] == t] for t in targets}
    empty = [t for t, got in found.items() if not got]
    filled = [t for t, got in found.items() if got]

    if not empty or not filled:
        return rows

    # 이미 검색어와 같은 표기로 물어봤다. 다른 표기를 찾아야 의미가 있다.
    asked = normalize_text(keyword)
    names = []
    for target in filled:
        for row in found[target]:
            for name in split_singers(row.get("singer")):
                if normalize_text(name) != asked and name not in names:
                    names.append(name)

    if not names:
        return rows

    # 가장 많이 나온 이름부터 쓴다. 검색 결과의 주인이 그 가수일 가능성이 높다.
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

    # 이 길이 통했다면 적어 둔다. 다음부터는 공식을 부르지 않는다.
    # 저장에 실패해도 검색은 그대로 진행한다.
    if gained:
        try:
            alias.remember(keyword, names[0])
        except Exception as exc:
            logger.info("별칭 저장 실패, 결과에는 영향 없습니다: %s", exc)

    return _merge(rows, gained)


def _fetch_brand(brand, keyword, search_type):
    """브랜드 하나의 결과를 가져온다. 소스 선택과 폴백을 담당한다.

    TJ·금영 모두 공식 사이트를 먼저 본다. 공식에만 있는 것이 있기 때문이다.
      - 금영: manana가 2026-04 이후 멈춰 최신곡이 통째로 빠진다
      - TJ  : manana에는 한글 발음 검색이 없다 ('요루시카' → manana 0건)

    공식은 HTML 파싱이라 사이트가 바뀌면 깨진다. 실패하거나 0건이면
    manana로 되돌아간다. 앱이 빈 화면을 보이는 것보다는 낫다.
    """
    rows = _fetch_official(brand, keyword, search_type)
    if rows is None:
        return manana.search(keyword, search_type=search_type, brand=brand)

    return _fill_release(rows, keyword, search_type, brand)


def _merge(primary, extra):
    """두 소스의 결과를 합친다. (브랜드, 곡번호)가 같으면 하나로 본다."""
    seen = {(row["brand"], row["no"]) for row in primary}
    merged = list(primary)

    for row in extra:
        key = (row["brand"], row["no"])
        if key not in seen:
            seen.add(key)
            merged.append(row)

    return merged


def _fetch_catalog(brand, keyword, search_type, full=False):
    """자체 DB를 먼저 보고, 필요하면 공식 사이트로 보강한다.

    두 단계로 나뉜다.
      full=False (기본) — DB만 본다. 0.03초. 결과가 전부가 아닐 수 있다.
      full=True        — 공식까지 뒤져 합친다. 4초.

    클라이언트는 1차로 빠르게 받아 그리고, complete가 false면
    곧바로 full=1로 다시 불러 뒤늦게 온 것을 아래에 덧붙인다.

    DB는 빠르지만(0.03초 vs 4.7초) 우리가 크롤링한 표기만 갖고 있다.
    한글 발음('요루시카')이나 로마자('kakeru')는 **공식 사이트의 검색
    인덱스에만 있고 화면에는 노출되지 않아** 크롤링으로 가져올 수 없다.
    그래서 DB가 못 찾은 검색어는 공식에 물어본다.

    DB 결과가 넉넉하면 공식은 부르지 않는다. 그래야 남의 서버 부담과
    응답 시간을 아낀다.
    """
    if not current_app.config["DB_SEARCH_ENABLED"]:
        return _fetch_official_all(brand, keyword, search_type), True

    rows = song.search(keyword, search_type, _target_brands(brand))

    if rows is None:
        # DB 장애. 예전처럼 외부만 본다.
        return _fetch_official_all(brand, keyword, search_type), True

    if not full:
        # 전에 배워 둔 발음이면 공식을 부르지 않고 DB로 답한다.
        learned = _search_by_alias(brand, keyword, search_type)
        if learned:
            return _merge(rows, learned), True

        # 공식을 더 찔러볼 이유가 있는지 판단한다.
        # 매번 찌르면 DB를 만든 의미가 없고, 아예 안 찌르면 한글 발음
        # 검색이 안 된다.
        #   - 결과 0건        → 확인 필요
        #   - 일본어가 아닌 검색어 → DB에 그 표기가 없다. 확인 필요
        #   - 그 외            → DB로 충분하다
        needs_official = not rows or not _JAPANESE.search(keyword)
        return rows, not needs_official

    logger.info("DB %d건, 공식으로 보강합니다: %r", len(rows), keyword)
    try:
        return _merge(rows, _fetch_official_all(brand, keyword, search_type)), True
    except Exception as exc:
        # 공식이 죽어도 DB 결과는 살린다
        logger.warning("공식 보강 실패, DB 결과만 씁니다: %s", exc)
        if rows:
            return rows, True
        raise


def _fetch_all_brands(brand, keyword, search_type):
    """요청한 브랜드들을 동시에 조회한다.

    직렬로 돌면 느린 쪽을 기다리는 만큼 그대로 더해진다
    (실측: TJ 0.7초 + 금영 4.4초 = 5.5초). 두 사이트는 서로 무관하므로
    같이 부르면 느린 쪽 시간으로 끝난다.
    """
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
                # 한 브랜드가 죽어도 다른 쪽 결과는 보여준다
                errors.append(exc)
                logger.warning("%s 조회 실패: %s", target, exc)
                return []

    rows = []
    with ThreadPoolExecutor(max_workers=len(targets)) as pool:
        for found in pool.map(fetch, targets):
            rows.extend(found)

    # 전부 실패했다면 상위에서 stale 캐시로 넘어가도록 알린다
    if errors and len(errors) == len(targets):
        raise errors[0]

    return rows


def _build_groups(items):
    """정규화 키(match_key)로 같은 곡을 브랜드 넘어 묶는다.

    TJ와 금영은 같은 곡을 띄어쓰기, 괄호 안 부가정보, 카타카나/히라가나
    표기까지 다르게 등록한다. normalize.make_match_key()가 그 차이를
    흡수하므로, 사용자는 한 곡에서 양쪽 번호를 한 번에 볼 수 있다.
    """
    groups = {}

    for item in items:
        group = groups.get(item["match_key"])
        if group is None:
            group = {
                # 대표 표기는 먼저 등장한 항목(= 최신 발매)을 쓴다.
                "title": item["title"],
                # 번역 제목은 있는 쪽을 쓴다. 같은 곡이라도 자체 DB에서 온
                # 항목에만 붙어 있어서, 대표 항목이 공식 결과면 비어 있다.
                "title_ko": item.get("title_ko", ""),
                "singer": item["singer"],
                "match_key": item["match_key"],
                "brands": {},
            }
            groups[item["match_key"]] = group

        group["brands"].setdefault(item["brand"], []).append(item["no"])

        # 뒤에 온 항목이 번역을 갖고 있으면 채운다 (앞 항목이 공식 결과였을 때)
        if not group["title_ko"] and item.get("title_ko"):
            group["title_ko"] = item["title_ko"]

    ordered = list(groups.values())
    for group in ordered:
        # 양쪽 기기에 모두 있는 곡인지 — 클라이언트에서 배지 표시용
        group["both"] = len(group["brands"]) > 1

    return ordered


def search(keyword, search_type="song", brand=ALL_BRANDS, limit=None, offset=None,
           full=False, sort=SORT_RELEASE, include_korean=False):
    """검색 결과를 브랜드별로 그룹핑해 반환한다."""
    keyword, search_type, brand = _validate(keyword, search_type, brand)
    limit, offset = _validate_paging(limit, offset)

    # 1차(DB만)와 2차(공식 포함)는 결과가 다르므로 캐시도 나눈다
    key = _cache_key(keyword, search_type, brand, include_korean)
    if not full:
        key += ":quick"
    cached = cache.get_json(key)

    if cached is not None:
        items = cached
        from_cache = True
        # 캐시된 것은 그 단계의 완성도를 그대로 따른다
        complete = full
    else:
        # brand를 생략한 manana 호출은 전 기기를 훑는 대신 잘린 결과를 준다.
        # (예: singer=Ado → 무브랜드 응답의 tj는 10건, tj 직접 호출은 70건)
        # 따라서 all 이어도 브랜드별로 각각 호출해서 합친다.
        try:
            if search_type == LYRICS_TYPE:
                raw = _fetch_lyrics(keyword, brand)
                complete = True
            else:
                raw, complete = _fetch_catalog(brand, keyword, search_type, full)
        except manana.MananaError:
            # 모든 소스가 실패했다. 만료된 사본이라도 있으면 그거라도 내보낸다.
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

    # 캐시에는 전체 결과를 담아두고, 응답에서만 잘라낸다.
    # 페이지를 넘길 때마다 manana를 다시 부르지 않기 위함이다.
    page = items if limit is None else items[offset : offset + limit]

    grouped = _group_by_brand(page, brand)
    groups = _build_groups(page)

    payload = {
        "brand": brand,
        "cached": from_cache,
        # total은 번호 수, songs는 곡 수다.
        # 화면은 같은 곡을 한 장으로 묶어 보여주므로 카드 수와 맞는 것은 songs다.
        # (태진 1 + 금영 1 = total 2 이지만 카드는 1장)
        "total": total,
        "songs": len(_build_groups(items)),
        # counts / matched / groups 는 모두 '현재 페이지' 기준이다.
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

    # false면 아직 전부가 아니다 — 클라이언트가 full=1로 다시 부른다
    payload["complete"] = complete

    if stale:
        # 업스트림이 죽어 만료된 사본을 내보냈다는 표시.
        # 클라이언트가 "정보가 오래됐을 수 있어요"를 띄울 수 있다.
        payload["stale"] = True

    if query is not None:
        payload["query"] = query
    if search_type is not None:
        payload["type"] = search_type

    return payload
