"""금영 공식 → manana 폴백 체인과 캐시 완충재."""

import pytest

from app.services import search_service
from app.services.kysing import KysingError
from app.services.manana import MananaError
from app.utils import cache
from tests.conftest import entry


@pytest.fixture
def sources(fake_manana, fake_kysing):
    """manana에는 옛 곡만, 공식에는 최신곡까지 있는 실제 상황."""
    fake_manana.by_brand["tj"] = [entry("tj", "68230", "花に亡霊", "ヨルシカ", "2026-02-01")]
    fake_manana.by_brand["kumyoung"] = [
        entry("kumyoung", "44693", "花に亡霊", "ヨルシカ", "2023-04-01")
    ]
    fake_kysing.rows = [
        entry("kumyoung", "44693", "花に亡霊", "ヨルシカ", "2023-04-01"),
        # manana가 못 가진 최신곡
        entry("kumyoung", "76542", "忘れてください", "ヨルシカ", "2026-06-01"),
    ]
    return fake_manana, fake_kysing


class TestSourceSelection:
    def test_kumyoung_prefers_official(self, app, sources):
        manana_rec, kysing_rec = sources
        with app.app_context():
            result = search_service.search("ヨルシカ", "singer", "kumyoung")

        assert kysing_rec.calls == [("singer", "ヨルシカ")]
        # 공식이 성공했으니 금영은 manana를 부르지 않는다
        assert manana_rec.calls == []
        assert result["counts"]["kumyoung"] == 2

    def test_tj_always_uses_manana(self, app, sources):
        manana_rec, kysing_rec = sources
        with app.app_context():
            search_service.search("ヨルシカ", "singer", "tj")

        assert manana_rec.calls == [("singer", "ヨルシカ", "tj")]
        assert kysing_rec.calls == []

    def test_all_mixes_both_sources(self, app, sources):
        manana_rec, kysing_rec = sources
        with app.app_context():
            result = search_service.search("ヨルシカ", "singer", "all")

        assert manana_rec.calls == [("singer", "ヨルシカ", "tj")]
        assert kysing_rec.calls == [("singer", "ヨルシカ")]
        assert result["counts"] == {"tj": 1, "kumyoung": 2}

    def test_official_brings_songs_manana_lacks(self, app, sources):
        with app.app_context():
            result = search_service.search("ヨルシカ", "singer", "kumyoung")

        numbers = {s["no"] for s in result["results"]["kumyoung"]}
        assert "76542" in numbers

    def test_can_be_disabled_by_config(self, app, sources):
        manana_rec, kysing_rec = sources
        app.config["KYSING_ENABLED"] = False
        with app.app_context():
            search_service.search("ヨルシカ", "singer", "kumyoung")

        assert kysing_rec.calls == []
        assert manana_rec.calls == [("singer", "ヨルシカ", "kumyoung")]


class TestFallback:
    def test_falls_back_when_official_errors(self, app, sources):
        manana_rec, kysing_rec = sources
        kysing_rec.error = KysingError("사이트 다운")

        with app.app_context():
            result = search_service.search("ヨルシカ", "singer", "kumyoung")

        assert manana_rec.calls == [("singer", "ヨルシカ", "kumyoung")]
        assert result["counts"]["kumyoung"] == 1

    def test_falls_back_when_parser_crashes(self, app, sources):
        """구조 변경으로 파서가 예외를 던져도 서비스는 살아야 한다."""
        manana_rec, kysing_rec = sources
        kysing_rec.error = AttributeError("마크업이 바뀜")

        with app.app_context():
            result = search_service.search("ヨルシカ", "singer", "kumyoung")

        assert result["counts"]["kumyoung"] == 1

    def test_falls_back_when_official_returns_nothing(self, app, sources):
        """파서가 조용히 0건을 뱉는 경우 — 가장 위험한 실패 방식."""
        manana_rec, kysing_rec = sources
        kysing_rec.rows = []

        with app.app_context():
            result = search_service.search("ヨルシカ", "singer", "kumyoung")

        assert manana_rec.calls == [("singer", "ヨルシカ", "kumyoung")]
        assert result["counts"]["kumyoung"] == 1


class TestStaleCache:
    def test_serves_stale_when_everything_fails(self, app, sources, fake_redis):
        manana_rec, kysing_rec = sources

        with app.app_context():
            first = search_service.search("ヨルシカ", "singer", "kumyoung")
            assert first["total"] == 2

            # 정상 캐시만 날리고 업스트림을 모두 죽인다
            for k in [k for k in fake_redis.store if not k.endswith(":stale")]:
                del fake_redis.store[k]
            kysing_rec.error = KysingError("다운")
            manana_rec.error = MananaError("업스트림 다운")

            result = search_service.search("ヨルシカ", "singer", "kumyoung")

        assert result["stale"] is True
        assert result["total"] == 2

    def test_raises_when_no_stale_copy(self, app, fake_manana, fake_kysing, fake_redis):
        fake_kysing.error = KysingError("다운")
        fake_manana.error = MananaError("업스트림 다운")

        with app.app_context(), pytest.raises(MananaError):
            search_service.search("처음보는가수", "singer", "kumyoung")

    def test_stale_copy_lives_longer(self, app, sources, fake_redis):
        with app.app_context():
            search_service.search("ヨルシカ", "singer", "kumyoung")

        normal = [k for k in fake_redis.ttls if not k.endswith(":stale")]
        stale = [k for k in fake_redis.ttls if k.endswith(":stale")]
        assert stale, "비상용 사본이 저장되어야 한다"
        assert fake_redis.ttls[stale[0]] > fake_redis.ttls[normal[0]]
        assert fake_redis.ttls[stale[0]] == cache.STALE_TTL


class TestHealthProbe:
    @pytest.fixture(autouse=True)
    def low_threshold(self, app):
        # 표본 픽스처가 소수의 곡만 갖고 있으므로 기준을 낮춘다
        app.config["PROBE_MIN_ROWS"] = 1

    def test_deep_health_reports_sources(self, client, sources):
        payload = client.get("/api/health?deep=1").get_json()
        assert payload["sources"]["kysing"]["ok"] is True
        assert payload["sources"]["manana"]["ok"] is True
        assert payload["status"] == "ok"

    def test_broken_parser_is_partial_not_down(self, client, sources):
        """공식이 깨져도 manana가 살아 있으면 서비스는 degraded가 아니다."""
        sources[1].rows = []
        payload = client.get("/api/health?deep=1").get_json()

        assert payload["sources"]["kysing"]["ok"] is False
        assert payload["status"] == "partial"

    def test_manana_down_is_degraded(self, client, sources):
        sources[0].error = MananaError("업스트림 다운")
        payload = client.get("/api/health?deep=1").get_json()

        assert payload["sources"]["manana"]["ok"] is False
        assert payload["status"] == "degraded"

    def test_shallow_health_skips_probes(self, client, sources):
        payload = client.get("/api/health").get_json()
        assert "sources" not in payload
        assert sources[1].calls == []


class TestOfficialForBothBrands:
    """TJ도 공식을 먼저 본다 — manana에는 한글 발음 검색이 없다."""

    def test_tj_prefers_official(self, app, fake_manana, fake_tjmedia):
        fake_tjmedia.rows = [entry("tj", "52504", "曲", "ヨルシカ", "2026-01-01")]
        with app.app_context():
            result = search_service.search("요루시카", "singer", "tj")

        assert fake_tjmedia.calls == [("singer", "요루시카")]
        assert fake_manana.calls == []
        assert result["counts"]["tj"] == 1

    def test_tj_falls_back_to_manana(self, app, fake_manana, fake_tjmedia):
        fake_tjmedia.error = RuntimeError("마크업 변경")
        fake_manana.by_brand["tj"] = [entry("tj", "68230", "曲", "ヨルシカ")]

        with app.app_context():
            result = search_service.search("ヨルシカ", "singer", "tj")

        assert result["counts"]["tj"] == 1
        assert fake_manana.calls == [("singer", "ヨルシカ", "tj")]

    def test_tj_can_be_disabled(self, app, fake_manana, fake_tjmedia):
        app.config["TJMEDIA_ENABLED"] = False
        fake_manana.by_brand["tj"] = [entry("tj", "68230", "曲", "ヨルシカ")]

        with app.app_context():
            search_service.search("ヨルシカ", "singer", "tj")

        assert fake_tjmedia.calls == []

    def test_missing_release_is_filled_from_manana(self, app, fake_manana, fake_tjmedia):
        """TJ 공식에는 발매일이 없다. 비워두면 정렬에서 아래로 밀린다."""
        fake_tjmedia.rows = [entry("tj", "68230", "曲", "ヨルシカ", "")]
        fake_manana.by_brand["tj"] = [entry("tj", "68230", "曲", "ヨルシカ", "2026-02-01")]

        with app.app_context():
            result = search_service.search("ヨルシカ", "singer", "tj")

        assert result["results"]["tj"][0]["release"] == "2026-02-01"

    def test_release_fill_failure_is_survivable(self, app, fake_manana, fake_tjmedia):
        fake_tjmedia.rows = [entry("tj", "68230", "曲", "ヨルシカ", "")]
        fake_manana.error = MananaError("다운")

        with app.app_context():
            result = search_service.search("ヨルシカ", "singer", "tj")

        assert result["counts"]["tj"] == 1


class TestLyricsSearch:
    """가사 인덱스는 금영에만 있다. TJ 번호는 제목으로 역조회한다."""

    @pytest.fixture
    def wired(self, fake_manana, fake_kysing, fake_tjmedia):
        fake_kysing.rows = [entry("kumyoung", "57775", "怪獣の花唄", "Vaundy", "2026-01-01")]
        fake_tjmedia.rows = [entry("tj", "52988", "怪獣の花唄", "Vaundy", "2026-01-01")]
        return fake_manana, fake_kysing, fake_tjmedia

    def test_searches_kysing_with_lyrics_category(self, app, wired):
        _, kysing_rec, _ = wired
        with app.app_context():
            search_service.search("眠れない", "lyrics", "all")

        assert kysing_rec.calls == [("lyrics", "眠れない")]

    def test_cross_looks_up_tj_by_title(self, app, wired):
        _, _, tj_rec = wired
        with app.app_context():
            result = search_service.search("眠れない", "lyrics", "all")

        # 금영에서 찾은 제목으로 TJ를 다시 뒤진다
        assert tj_rec.calls == [("song", "怪獣の花唄")]
        assert result["counts"] == {"tj": 1, "kumyoung": 1}
        # 같은 곡이므로 한 그룹으로 묶여야 한다
        assert result["matched"] == 1

    def test_kumyoung_only_skips_cross_lookup(self, app, wired):
        _, _, tj_rec = wired
        with app.app_context():
            result = search_service.search("眠れない", "lyrics", "kumyoung")

        assert tj_rec.calls == []
        assert result["counts"] == {"kumyoung": 1}

    def test_tj_lookup_failure_does_not_break_search(self, app, wired):
        _, _, tj_rec = wired
        tj_rec.error = RuntimeError("깨짐")

        with app.app_context():
            result = search_service.search("眠れない", "lyrics", "all")

        # TJ가 실패해도 금영 결과는 나온다
        assert result["counts"]["kumyoung"] == 1

    def test_cross_lookup_is_capped(self, app, fake_manana, fake_kysing, fake_tjmedia):
        """결과가 많아도 TJ 역조회 횟수에 상한이 있어야 한다."""
        fake_kysing.rows = [
            entry("kumyoung", str(i), f"곡{i}", "가수", "2026-01-01") for i in range(40)
        ]
        with app.app_context():
            search_service.search("눈물", "lyrics", "all")

        assert len(fake_tjmedia.calls) == search_service.LYRICS_CROSS_LOOKUP_LIMIT

    def test_endpoint_accepts_lyrics_type(self, client, wired):
        res = client.get("/api/search?q=眠れない&type=lyrics&brand=all")
        assert res.status_code == 200
        assert res.get_json()["type"] == "lyrics"
