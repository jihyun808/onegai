"""자체 DB 우선 조회 + 공식 보강, 크롤러 안전장치."""

from datetime import date, timedelta

import pytest

from app.models import song
from app.services import crawler, search_service
from tests.conftest import entry


@pytest.fixture
def fake_db(monkeypatch):
    """songs 테이블 조회를 가로챈다."""

    class Recorder:
        def __init__(self):
            self.rows = []
            self.calls = []
            self.unavailable = False

        def search(self, keyword, search_type, brands, limit=500):
            self.calls.append((search_type, keyword, tuple(brands)))
            return None if self.unavailable else list(self.rows)

    recorder = Recorder()
    monkeypatch.setattr(song, "search", recorder.search)
    return recorder


@pytest.fixture
def wired(fake_manana, fake_kysing, fake_tjmedia):
    fake_tjmedia.rows = [entry("tj", "68381", "夜に駆ける", "YOASOBI", "2026-01-01")]
    fake_kysing.rows = [entry("kumyoung", "44656", "夜に駆ける", "YOASOBI", "2026-01-01")]
    return fake_manana, fake_kysing, fake_tjmedia


class TestTwoPhase:
    """1차는 DB만(빠름), 2차는 공식까지(느림). complete로 구분한다."""

    def test_japanese_query_with_results_is_complete(self, app, fake_db, wired):
        """일본어 검색어는 DB가 답할 수 있다. 공식을 부르지 않는다."""
        fake_db.rows = [
            entry("tj", str(i), f"곡{i}", "ヨルシカ", "2026-01-01") for i in range(5)
        ]
        with app.app_context():
            result = search_service.search("ヨルシカ", "singer", "all")

        assert result["total"] == 5
        assert result["complete"] is True
        assert wired[2].calls == []
        assert wired[1].calls == []

    def test_korean_query_needs_official(self, app, fake_db, wired):
        """한글 발음은 공식 인덱스에만 있다. 결과가 있어도 확인해야 한다."""
        fake_db.rows = [entry("tj", "1", "곡", "요루시카", "2026-01-01")]
        with app.app_context():
            result = search_service.search("요루시카", "singer", "all")

        assert result["complete"] is False

    def test_romaji_query_needs_official(self, app, fake_db, wired):
        fake_db.rows = [entry("tj", "1", "곡", "가수", "2026-01-01")]
        with app.app_context():
            result = search_service.search("kakeru", "song", "all")

        assert result["complete"] is False

    def test_empty_db_result_needs_official(self, app, fake_db, wired):
        """일본어라도 DB가 못 찾으면 확인한다 — 미크롤링 신곡일 수 있다."""
        fake_db.rows = []
        with app.app_context():
            result = search_service.search("メズマライザー", "song", "all")

        assert result["complete"] is False

    def test_full_pass_queries_official(self, app, fake_db, wired):
        fake_db.rows = []
        with app.app_context():
            result = search_service.search("요루시카", "singer", "all", full=True)

        assert wired[2].calls == [("singer", "요루시카")]
        assert result["total"] == 2
        assert result["complete"] is True

    def test_full_pass_merges_without_duplicates(self, app, fake_db, wired):
        fake_db.rows = [entry("tj", "68381", "夜に駆ける", "YOASOBI", "2026-01-01")]
        with app.app_context():
            result = search_service.search("요루니카케루", "song", "all", full=True)

        assert [s["no"] for s in result["results"]["tj"]] == ["68381"]
        assert result["total"] == 2

    def test_phases_use_separate_cache(self, app, fake_db, wired, fake_redis):
        """1차 결과가 2차 요청에 재사용되면 안 된다."""
        # 가수명을 공식 응답과 맞춘다. 다르게 두면 노이즈 필터가 공식 결과를
        # 걷어내 이 테스트가 캐시가 아니라 필터를 재는 것이 된다.
        fake_db.rows = [entry("tj", "1", "アイドル", "YOASOBI", "2026-01-01")]
        with app.app_context():
            quick = search_service.search("YOASOBI", "singer", "all")
            full = search_service.search("YOASOBI", "singer", "all", full=True)

        assert quick["total"] == 1
        assert full["total"] == 3  # DB 1 + 공식 2
        assert full["complete"] is True

    def test_endpoint_accepts_full_flag(self, client, fake_db, wired):
        fake_db.rows = []
        assert client.get("/api/search?q=x").get_json()["complete"] is False
        assert client.get("/api/search?q=x&full=1").get_json()["complete"] is True


class TestDbFirst:

    def test_db_outage_falls_back_to_official(self, app, fake_db, wired):
        fake_db.unavailable = True
        with app.app_context():
            result = search_service.search("ヨルシカ", "singer", "all")
        assert result["complete"] is True

        assert result["total"] == 2
        assert wired[2].calls

    def test_official_failure_keeps_db_results(self, app, fake_db, wired):
        """공식이 죽어도 DB가 찾은 것은 보여준다."""
        fake_db.rows = [entry("tj", "1", "곡", "ヨルシカ", "2026-01-01")]
        wired[1].error = RuntimeError("금영 다운")
        wired[2].error = RuntimeError("TJ 다운")
        wired[0].error = None
        wired[0].by_brand = {}

        with app.app_context():
            result = search_service.search("ヨルシカ", "singer", "all", full=True)

        assert result["total"] == 1

    def test_can_be_disabled(self, app, fake_db, wired):
        app.config["DB_SEARCH_ENABLED"] = False
        with app.app_context():
            search_service.search("ヨルシカ", "singer", "all")

        assert fake_db.calls == []


class TestCrawlerSafety:
    def test_drops_unreleased_songs(self):
        """발매 예정곡은 받지 않는다 — 번호를 눌러도 기계에 곡이 없다."""
        future = (date.today() + timedelta(days=60)).isoformat()
        past = (date.today() - timedelta(days=60)).isoformat()

        kept = crawler._drop_unreleased(
            [
                entry("kumyoung", "1", "나온 곡", "가수", past),
                entry("kumyoung", "2", "예정곡", "가수", future),
                entry("kumyoung", "3", "날짜 없음", "가수", ""),
            ]
        )

        assert [row["no"] for row in kept] == ["1", "3"]

    def test_throttles_requests(self, monkeypatch):
        """남의 서버다. 요청 사이에 간격을 둔다."""
        slept = []
        monkeypatch.setattr(crawler.time, "sleep", lambda s: slept.append(s))
        monkeypatch.setattr(crawler.time, "monotonic", lambda: 0.0)

        crawler._last_request[0] = 0.0
        crawler._wait_turn()
        crawler._wait_turn()

        assert slept, "간격 없이 연속 호출되면 안 된다"
        assert all(s <= crawler.REQUEST_DELAY for s in slept)

    def test_backfill_concurrency_is_modest(self):
        assert crawler.BACKFILL_WORKERS <= 3
        assert crawler.REQUEST_DELAY > 0

    def test_months_covers_range(self):
        got = crawler.months(date(2025, 11, 1), date(2026, 2, 1))
        assert got == ["202511", "202512", "202601", "202602"]


class TestKoreanNoiseFilter:
    """일본곡 앱이므로 딸려 온 한국곡은 감춘다."""

    def test_hides_korean_song(self, app, fake_db, wired):
        fake_db.rows = [
            entry("tj", "1", "Let's Get Together (드라마\"미미쿠스\")", "ATEEZ(에이티즈)"),
            entry("tj", "2", "初音ミクの消失", "cosMo@暴走P feat.初音ミク"),
        ]
        with app.app_context():
            result = search_service.search("미쿠", "song", "all", full=True)

        titles = [g["title"] for g in result["groups"]]
        assert "初音ミクの消失" in titles
        assert not any("미미쿠스" in t for t in titles)

    def test_keeps_romaji_japanese_song(self, app, fake_db, wired):
        """한글이 없으면 거르지 않는다 — YOASOBI의 'Idol' 같은 경우."""
        fake_db.rows = [entry("tj", "1", "Idol", "YOASOBI")]
        with app.app_context():
            result = search_service.search("Idol", "song", "all", full=True)

        assert "Idol" in [g["title"] for g in result["groups"]]

    def test_keeps_japanese_song_with_korean_annotation(self, app, fake_db, wired):
        """제목에 한글이 섞여도 일본어가 있으면 남긴다."""
        fake_db.rows = [entry("tj", "1", "残酷な天使のテーゼ (에반게리온 OP)", "高橋洋子")]
        with app.app_context():
            result = search_service.search("에반게리온", "song", "all", full=True)

        assert any("残酷な天使のテーゼ" in g["title"] for g in result["groups"])


class TestTjHighlightParsing:
    """TJ는 검색어 일치 부분을 <span class='highlight'>로 감싼다."""

    def test_highlight_does_not_split_name(self):
        from app.services import tjmedia

        block = (
            '<ul class="grid-container list ico">'
            '<li class="grid-item center pos-type"><p><span>68395</span></p></li>'
            '<li class="grid-item title3"><p><span>Under the <span class=\'highlight\'>Sky</span></span></p></li>'
            "<li class=\"grid-item title4 singer\"><p><span>Do As <span class='highlight'>Infinity</span></span></p></li>"
            '<li class="grid-item title5"><p><span>작사</span></p></li>'
            '<li class="grid-item title6"><p><span>작곡</span></p></li>'
            "</ul></li>"
        )
        rows = tjmedia._parse(block)

        assert rows[0]["singer"] == "Do As Infinity"
        assert rows[0]["title"] == "Under the Sky"
