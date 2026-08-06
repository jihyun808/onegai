"""검색 서비스 및 엔드포인트."""

import pytest

from app.services import search_service
from app.services.manana import MananaError
from tests.conftest import entry


@pytest.fixture
def two_brands(fake_manana):
    """TJ와 금영이 같은 곡을 다르게 등록한 상황."""
    fake_manana.by_brand["tj"] = [
        entry("tj", "68230", "花に亡霊(映画'泣きたい私は猫をかぶる' OST)", "ヨルシカ", "2026-02-01"),
        entry("tj", "68212", "雨とカプチーノ", "ヨルシカ", "2026-01-05"),
    ]
    fake_manana.by_brand["kumyoung"] = [
        entry("kumyoung", "44693", '花に亡霊 ("泣きたい私は猫をかぶる"OST)', "ヨルシカ", "2026-01-20"),
    ]
    return fake_manana


class TestValidation:
    def test_empty_keyword(self, client):
        res = client.get("/api/search?q=")
        assert res.status_code == 400
        assert res.get_json()["error"] == "invalid_request"

    def test_missing_keyword(self, client):
        assert client.get("/api/search").status_code == 400

    def test_too_long_keyword(self, client):
        res = client.get("/api/search", query_string={"q": "가" * 101})
        assert res.status_code == 400

    def test_unsupported_brand(self, client):
        """joysound / dam 은 기획상 노출하지 않는다."""
        res = client.get("/api/search?q=Ado&brand=joysound")
        assert res.status_code == 400

    def test_unsupported_type(self, client):
        assert client.get("/api/search?q=Ado&type=composer").status_code == 400

    def test_upstream_failure_is_502(self, client, monkeypatch):
        from app.services import manana

        def boom(*args, **kwargs):
            raise MananaError("실패")

        monkeypatch.setattr(manana, "search", boom)
        res = client.get("/api/search?q=Ado")
        assert res.status_code == 502
        assert res.get_json()["error"] == "upstream_error"


class TestBrandFanout:
    def test_all_calls_each_brand_separately(self, app, two_brands):
        """무브랜드 manana 호출은 잘린 결과를 주므로 쓰면 안 된다."""
        with app.app_context():
            search_service.search("ヨルシカ", "singer", "all")

        assert two_brands.calls == [
            ("singer", "ヨルシカ", "tj"),
            ("singer", "ヨルシカ", "kumyoung"),
        ]
        # brand=None 으로 부른 적이 없어야 한다
        assert all(brand is not None for _, _, brand in two_brands.calls)

    def test_all_is_union_of_brands(self, app, two_brands):
        with app.app_context():
            result = search_service.search("ヨルシカ", "singer", "all")

        assert result["total"] == 3
        assert result["counts"] == {"tj": 2, "kumyoung": 1}

    def test_single_brand_calls_once(self, app, two_brands):
        with app.app_context():
            result = search_service.search("ヨルシカ", "singer", "tj")

        assert two_brands.calls == [("singer", "ヨルシカ", "tj")]
        assert result["counts"] == {"tj": 2}

    def test_requested_brand_present_even_when_empty(self, app, fake_manana):
        with app.app_context():
            result = search_service.search("없는가수", "singer", "all")

        assert result["total"] == 0
        assert result["results"] == {"tj": [], "kumyoung": []}


class TestGrouping:
    def test_cross_brand_songs_are_grouped(self, app, two_brands):
        with app.app_context():
            result = search_service.search("ヨルシカ", "singer", "all")

        assert result["matched"] == 1
        matched = [g for g in result["groups"] if g["both"]]
        assert matched[0]["brands"] == {"tj": ["68230"], "kumyoung": ["44693"]}

    def test_single_brand_song_is_not_matched(self, app, two_brands):
        with app.app_context():
            result = search_service.search("ヨルシカ", "singer", "all")

        solo = [g for g in result["groups"] if not g["both"]]
        assert [g["brands"] for g in solo] == [{"tj": ["68212"]}]

    def test_group_keeps_every_number(self, app, fake_manana):
        """괄호 제거로 버전 표기가 병합돼도 번호는 잃지 않는다."""
        fake_manana.by_brand["kumyoung"] = [
            entry("kumyoung", "88397", "花に亡霊(Acoustic Ver.)", "ヨルシカ"),
            entry("kumyoung", "46438", "花に亡霊", "ヨルシカ"),
        ]
        with app.app_context():
            result = search_service.search("ヨルシカ", "singer", "kumyoung")

        assert len(result["groups"]) == 1
        assert sorted(result["groups"][0]["brands"]["kumyoung"]) == ["46438", "88397"]

    def test_results_keep_original_titles(self, app, two_brands):
        """원본 필드는 정규화로 변형되지 않는다."""
        with app.app_context():
            result = search_service.search("ヨルシカ", "singer", "all")

        assert result["results"]["tj"][0]["title"] == (
            "花に亡霊(映画'泣きたい私は猫をかぶる' OST)"
        )


class TestSorting:
    def test_newest_first(self, app, two_brands):
        with app.app_context():
            result = search_service.search("ヨルシカ", "singer", "all")

        releases = [i["release"] for i in result["results"]["tj"]]
        assert releases == sorted(releases, reverse=True)


class TestCaching:
    def test_second_call_hits_cache(self, app, two_brands, fake_redis):
        with app.app_context():
            first = search_service.search("ヨルシカ", "singer", "tj")
            second = search_service.search("ヨルシカ", "singer", "tj")

        assert first["cached"] is False
        assert second["cached"] is True
        assert len(two_brands.calls) == 1

    def test_case_and_space_variants_share_cache(self, app, fake_manana, fake_redis):
        fake_manana.by_brand["tj"] = [entry("tj", "1", "곡", "YOASOBI")]
        with app.app_context():
            search_service.search("YOASOBI", "singer", "tj")
            result = search_service.search("  yoasobi ", "singer", "tj")

        assert result["cached"] is True
        assert len(fake_manana.calls) == 1

    def test_distinct_queries_do_not_share_cache(self, app, fake_manana, fake_redis):
        """'ONE PIECE' 와 'ONEPIECE' 는 manana가 다르게 취급한다."""
        fake_manana.by_brand["tj"] = [entry("tj", "1", "곡", "가수")]
        with app.app_context():
            search_service.search("ONE PIECE", "song", "tj")
            result = search_service.search("ONEPIECE", "song", "tj")

        assert result["cached"] is False
        assert len(fake_manana.calls) == 2

    def test_empty_result_uses_short_ttl(self, app, fake_manana, fake_redis):
        with app.app_context():
            search_service.search("없는곡", "song", "tj")

        ttl = next(iter(fake_redis.ttls.values()))
        assert ttl == search_service.EMPTY_CACHE_TTL

    def test_normal_result_uses_full_ttl(self, app, two_brands, fake_redis):
        with app.app_context():
            search_service.search("ヨルシカ", "singer", "tj")

        ttl = next(iter(fake_redis.ttls.values()))
        assert ttl == app.config["CACHE_TTL"]

    def test_works_without_redis(self, app, two_brands):
        """Redis가 없어도 검색은 동작해야 한다 (no_real_redis 픽스처 적용 중)."""
        with app.app_context():
            result = search_service.search("ヨルシカ", "singer", "all")

        assert result["total"] == 3
        assert result["cached"] is False

PAGING_KEYS = {"limit", "offset", "returned", "has_more"}


class TestResponseShape:
    def test_search_payload_keys(self, client, two_brands):
        payload = client.get("/api/search?q=ヨルシカ&type=singer&brand=all").get_json()
        assert set(payload) == {
            "query", "type", "brand", "cached",
            "total", "songs", "counts", "matched", "results", "groups", "complete",
        } | PAGING_KEYS

    def test_non_ascii_is_not_escaped(self, client, two_brands):
        """일본어/한글이 \\uXXXX 로 부풀지 않아야 한다."""
        res = client.get("/api/search?q=ヨルシカ&type=singer&brand=all")
        assert "ヨルシカ" in res.get_data(as_text=True)
        assert "\\u30e8" not in res.get_data(as_text=True)

    def test_health(self, client):
        payload = client.get("/api/health").get_json()
        assert payload["status"] == "ok"
        assert payload["redis"] is False  # 테스트에서는 캐시 비활성


class TestSongCount:
    """화면은 같은 곡을 한 장으로 묶는다. 숫자도 그에 맞아야 한다."""

    def test_songs_counts_cards_not_numbers(self, app, two_brands):
        with app.app_context():
            result = search_service.search("ヨルシカ", "singer", "all")

        # 花に亡霊은 양쪽에 있어 번호가 2개, 카드는 1장
        assert result["total"] == 3, "번호 수"
        assert result["songs"] == 2, "곡 수 = 카드 수"
        assert result["songs"] == len(result["groups"])

    def test_songs_covers_all_pages(self, app, fake_manana):
        """페이지에 잘려도 전체 곡 수를 알려줘야 한다."""
        fake_manana.by_brand["tj"] = [
            entry("tj", str(i), f"曲{i}", "ヨルシカ", "2026-01-01") for i in range(80)
        ]
        with app.app_context():
            result = search_service.search("ヨルシカ", "singer", "tj", limit=10)

        assert result["songs"] == 80
        assert len(result["groups"]) == 10


class TestSortOption:
    @pytest.fixture
    def mixed(self, fake_manana):
        # 번호와 발매일 순서가 어긋나게 둔다 — 정렬이 실제로 바뀌는지 보려고
        fake_manana.by_brand["tj"] = [
            entry("tj", "10", "曲A", "ヨルシカ", "2020-01-01"),
            entry("tj", "90", "曲B", "ヨルシカ", "2010-01-01"),
            entry("tj", "50", "曲C", "ヨルシカ", "2026-01-01"),
        ]
        return fake_manana

    def _numbers(self, result):
        return [s["no"] for s in result["results"]["tj"]]

    def test_release_order_is_default(self, app, mixed):
        with app.app_context():
            result = search_service.search("ヨルシカ", "singer", "tj")
        assert self._numbers(result) == ["50", "10", "90"]

    def test_number_order(self, app, mixed):
        with app.app_context():
            result = search_service.search("ヨルシカ", "singer", "tj", sort="no")
        assert self._numbers(result) == ["90", "50", "10"]

    def test_number_order_is_numeric_not_lexical(self, app, fake_manana):
        """문자열로 정렬하면 9가 10보다 뒤로 간다."""
        fake_manana.by_brand["tj"] = [
            entry("tj", n, f"曲{n}", "ヨルシカ", "2026-01-01") for n in ["9", "10", "100"]
        ]
        with app.app_context():
            result = search_service.search("ヨルシカ", "singer", "tj", sort="no")
        assert self._numbers(result) == ["100", "10", "9"]


class TestKoreanToggle:
    @pytest.fixture
    def mixed(self, fake_manana):
        fake_manana.by_brand["tj"] = [
            entry("tj", "1", "初音ミクの消失", "cosMo@暴走P"),
            entry("tj", "2", "구해 줘 (드라마\"미미쿠스\")", "ENHYPEN"),
        ]
        return fake_manana

    def test_hidden_by_default(self, app, mixed):
        with app.app_context():
            result = search_service.search("미쿠", "song", "tj", full=True)
        assert [g["title"] for g in result["groups"]] == ["初音ミクの消失"]

    def test_shown_when_enabled(self, app, mixed):
        with app.app_context():
            result = search_service.search(
                "미쿠", "song", "tj", full=True, include_korean=True
            )
        assert len(result["groups"]) == 2

    def test_uses_separate_cache(self, app, mixed, fake_redis):
        """켜고 끈 결과가 서로 섞이면 안 된다."""
        with app.app_context():
            search_service.search("미쿠", "song", "tj", full=True)
            with_korean = search_service.search(
                "미쿠", "song", "tj", full=True, include_korean=True
            )
        assert len(with_korean["groups"]) == 2
