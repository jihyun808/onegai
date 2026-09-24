import pytest

from app.utils.normalize import (
    make_match_key,
    normalize_query,
    normalize_text,
    split_singers,
)


@pytest.mark.parametrize(
    "left,right,rule",
    [
        ("봄 사랑 벚꽃 말고", "봄사랑벚꽃말고", "1. 공백 제거"),
        ("Ｔｏｔ　Ｍｕｓｉｃａ", "Tot Musica", "2. 전각 영숫자"),
        ("ﾚﾃﾞｨﾒｲﾄﾞ", "レディメイド", "2. 반각 가타카나"),
        ("ｽﾞﾄﾞﾝ", "ズドン", "2. 반각 탁점"),
        ("花に亡霊 (\"泣きたい私は猫をかぶる\"OST)", "花に亡霊", "3. 괄호 제거"),
        ("アイドル【推しの子】", "アイドル", "3. 일본어 괄호"),
        ("夜に駆ける(YOASOBI (Official))", "夜に駆ける", "3. 중첩 괄호"),
        ("Tot Musica(ウタ)..", "Tot Musica", "3. 금영 생략표기"),
        ("Take A Bow", "Take a bow", "4. 대소문자"),
        ("レディメイド", "れでぃめいど", "5. 카타카나/히라가나"),
        ("ヴィラン", "ゔぃらん", "5. ヴ"),
        ("ｱｲﾄﾞﾙ　（ＴＶサイズ）..", "あいどる", "종합"),
    ],
)
def test_normalize_text_matches(left, right, rule):
    assert normalize_text(left) == normalize_text(right), rule


@pytest.mark.parametrize(
    "left,right",
    [
        ("メイド", "メード"),
        ("夜に駆ける", "朝に駆ける"),
        ("ABC", "ABD"),
    ],
)
def test_normalize_text_keeps_distinct(left, right):
    assert normalize_text(left) != normalize_text(right)


def test_normalize_text_empty():
    assert normalize_text("") == ""
    assert normalize_text(None) == ""


@pytest.mark.parametrize(
    "singer,expected",
    [
        ("High4,아이유", ["High4", "아이유"]),
        ("Ado feat. XX", ["Ado", "XX"]),
        ("A ft. B", ["A", "B"]),
        ("Daft Punk", ["Daft Punk"]),
        ("Aftermath", ["Aftermath"]),
        ("Left Eye", ["Left Eye"]),
    ],
)
def test_split_singers(singer, expected):
    assert split_singers(singer) == expected


def test_match_key_ignores_singer_order():
    assert make_match_key("봄 사랑 벚꽃 말고", "High4,아이유") == make_match_key(
        "봄사랑벚꽃말고", "아이유, High4"
    )


def test_match_key_cross_brand_real_case():
    tj = make_match_key("花に亡霊(映画'泣きたい私は猫をかぶる' OST)", "ヨルシカ")
    kumyoung = make_match_key("花に亡霊 (\"泣きたい私は猫をかぶる\"OST)", "ヨルシカ")
    assert tj == kumyoung


class TestNormalizeQuery:

    def test_absorbs_case_and_width(self):
        assert normalize_query("  YOASOBI ") == normalize_query("ＹＯＡＳＯＢＩ")

    def test_keeps_distinct_queries_apart(self):
        assert normalize_query("ONE PIECE") != normalize_query("ONEPIECE")

    def test_collapses_repeated_whitespace(self):
        assert normalize_query("ONE   PIECE") == normalize_query("ONE PIECE")
