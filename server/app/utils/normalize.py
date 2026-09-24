import re
import unicodedata

_BRACKET_OPEN = "（［｛〔〈《「『【〖"
_BRACKET_CLOSE = "）］｝〕〉》」』】〗"

_BRACKET_TABLE = str.maketrans(
    _BRACKET_OPEN + _BRACKET_CLOSE + "[]{}",
    "(" * len(_BRACKET_OPEN) + ")" * len(_BRACKET_CLOSE) + "()" * 2,
)

_PAREN_BLOCK = re.compile(r"\([^()]*\)")

_NON_WORD = re.compile(r"[^\w]", re.UNICODE)

_TRAILING_ELLIPSIS = re.compile(r"(\.{2,}|…)+$")

_KATAKANA_START, _KATAKANA_END = 0x30A1, 0x30F6
_KANA_OFFSET = 0x60

_KANA_TABLE = {
    cp: cp - _KANA_OFFSET for cp in range(_KATAKANA_START, _KATAKANA_END + 1)
}


def fold_kana(text):

    return text.translate(_KANA_TABLE)


def normalize_text(value, strip_parens=True):

    if not value:
        return ""

    text = unicodedata.normalize("NFKC", str(value))
    text = text.translate(_BRACKET_TABLE)
    text = _TRAILING_ELLIPSIS.sub("", text.strip())

    if strip_parens:
        while True:
            stripped = _PAREN_BLOCK.sub(" ", text)
            if stripped == text:
                break
            text = stripped

    text = _NON_WORD.sub("", text)
    return fold_kana(text.casefold())


_SINGER_DELIM = re.compile(r"[,/&]|\bfeat\b\.?|\bft\b\.?", re.IGNORECASE)


_WHITESPACE = re.compile(r"\s+")


def normalize_query(value):

    if not value:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    return _WHITESPACE.sub(" ", text).strip().casefold()


def split_singers(singer):
    if not singer:
        return []
    parts = _SINGER_DELIM.split(str(singer))
    return [p.strip() for p in parts if p.strip()]


def make_match_key(title, singer):

    singer_key = "|".join(sorted(filter(None, (normalize_text(s) for s in split_singers(singer)))))
    return f"{normalize_text(title)}::{singer_key}"


def normalize_entry(entry):
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
        "title_ko": entry.get("title_ko") or "",
        "match_key": make_match_key(title, singer),
    }


def normalize_entries(entries):
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
