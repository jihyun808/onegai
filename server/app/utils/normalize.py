"""검색 결과 정규화 유틸.

TJ와 금영은 같은 곡을 서로 다른 표기로 등록한다.
브랜드 간 결과를 매칭하기 위해 비교 전용 키(match_key)를 만든다.
원본 필드는 변형하지 않고 그대로 보존한다.

적용하는 정규화:
1. 공백 제거
2. 전각/반각 통일 (NFKC — 전각 영숫자, 반각 가타카나 등)
3. 괄호 안 부가정보 제거 (애니 타이틀, OST 표기 등)
4. 대소문자 무시
5. 카타카나 → 히라가나 폴딩 (레디메이드를 어느 쪽으로 등록했든 매칭)
"""

import re
import unicodedata

# 괄호류: 전각/반각/대괄호/중괄호/일본어 괄호를 모두 () 로 통일
_BRACKET_OPEN = "（［｛〔〈《「『【〖"
_BRACKET_CLOSE = "）］｝〕〉》」』】〗"

_BRACKET_TABLE = str.maketrans(
    _BRACKET_OPEN + _BRACKET_CLOSE + "[]{}",
    "(" * len(_BRACKET_OPEN) + ")" * len(_BRACKET_CLOSE) + "()" * 2,
)

# 괄호로 감싼 부속 정보: (映画 OST), (feat. XX), (Inst.) 등
_PAREN_BLOCK = re.compile(r"\([^()]*\)")

# 비교에 의미 없는 기호. 문자/숫자만 남긴다.
_NON_WORD = re.compile(r"[^\w]", re.UNICODE)

# 금영이 제목 뒤에 붙이는 생략 표기 (".." / "…")
_TRAILING_ELLIPSIS = re.compile(r"(\.{2,}|…)+$")

# 카타카나 → 히라가나 폴딩.
# 브랜드마다 같은 곡을 「レディメイド」/「れでぃめいど」처럼 다르게 등록하므로
# 한쪽으로 접어서 비교한다. NFKC를 먼저 돌리므로 반각 가타카나(ﾚﾃﾞｨ)도 포함된다.
#
# ア(30A1)~ヴ(30F6) 만 접는다. ヷヸヹヺ(30F7~30FA)는 대응하는 히라가나가 없다.
# 장음 부호 'ー'는 남긴다 — 'メイド'와 'メード'는 실제로 다른 표기다.
_KATAKANA_START, _KATAKANA_END = 0x30A1, 0x30F6
_KANA_OFFSET = 0x60  # 카타카나 코드포인트 - 0x60 = 히라가나

_KANA_TABLE = {
    cp: cp - _KANA_OFFSET for cp in range(_KATAKANA_START, _KATAKANA_END + 1)
}


def fold_kana(text):
    """카타카나를 히라가나로 접는다.

    NFKC 이후에 호출해야 한다. 반각 가타카나와 탁점/반탁점 조합
    (ﾊﾞ → バ)이 먼저 합성되어야 정확히 접힌다.
    """
    return text.translate(_KANA_TABLE)


def normalize_text(value, strip_parens=True):
    """비교용 정규화 문자열을 만든다.

    - NFKC 정규화: 전각 영숫자/반각 가타카나를 표준형으로 통일
    - 괄호 안 부속 정보 제거
    - 공백/특수문자 제거
    - 영문 소문자화
    - 카타카나 → 히라가나 폴딩
    """
    if not value:
        return ""

    text = unicodedata.normalize("NFKC", str(value))
    text = text.translate(_BRACKET_TABLE)
    text = _TRAILING_ELLIPSIS.sub("", text.strip())

    if strip_parens:
        # 중첩 괄호를 고려해 더 이상 줄지 않을 때까지 반복 제거
        while True:
            stripped = _PAREN_BLOCK.sub(" ", text)
            if stripped == text:
                break
            text = stripped

    text = _NON_WORD.sub("", text)
    return fold_kana(text.casefold())


# 구분자. feat / ft 는 단어 경계를 강제해야 한다.
# (없으면 'Daft Punk' 가 'Da' + 'Punk' 로, 'Aftermath' 가 'A' + 'ermath' 로 쪼개진다)
_SINGER_DELIM = re.compile(r"[,/&]|\bfeat\b\.?|\bft\b\.?", re.IGNORECASE)


_WHITESPACE = re.compile(r"\s+")


def normalize_query(value):
    """캐시 키에 쓰는 검색어 정규화.

    match_key 와 달리 공백/기호를 제거하면 안 된다.
    manana는 'ONE PIECE'(결과 없음)와 'ONEPIECE'(결과 있음)를
    다르게 취급하므로, 둘이 같은 키가 되면 서로의 결과가 섞인다.
    표기 흔들림(대소문자, 전각, 연속 공백)만 흡수한다.
    """
    if not value:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    return _WHITESPACE.sub(" ", text).strip().casefold()


def split_singers(singer):
    """'High4,아이유' 처럼 콤마/슬래시로 묶인 가수명을 분리한다."""
    if not singer:
        return []
    parts = _SINGER_DELIM.split(str(singer))
    return [p.strip() for p in parts if p.strip()]


def make_match_key(title, singer):
    """브랜드 간 동일 곡 매칭에 쓰는 키.

    가수는 표기 순서가 브랜드마다 달라서(예: 'A,B' vs 'B,A')
    분리 후 정렬하여 순서 차이를 흡수한다.
    """
    singer_key = "|".join(sorted(filter(None, (normalize_text(s) for s in split_singers(singer)))))
    return f"{normalize_text(title)}::{singer_key}"


def normalize_entry(entry):
    """manana API 항목 하나를 서버 응답 스키마로 변환한다."""
    title = entry.get("title") or ""
    singer = entry.get("singer") or ""

    return {
        "brand": entry.get("brand") or "",
        "no": entry.get("no") or "",
        "title": title,
        "singer": singer,
        "composer": entry.get("composer") or "",
        "lyricist": entry.get("lyricist") or "",
        "release": entry.get("release") or "",
        "match_key": make_match_key(title, singer),
    }


def normalize_entries(entries):
    """리스트 정규화. 같은 브랜드 내 (brand, no) 중복은 제거한다."""
    seen = set()
    results = []

    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        item = normalize_entry(entry)
        dedup_key = (item["brand"], item["no"])
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        results.append(item)

    return results
