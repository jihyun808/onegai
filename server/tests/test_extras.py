"""번역 · 미리듣기 · 가사. 핵심은 '키가 없어도 안 터진다'."""

import pytest
import requests

from app.services import kysing, lyrics, preview, translate
from app.services.search_service import _cache_key
from app.utils import cache
from app.utils.normalize import normalize_text


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            err = requests.HTTPError(f"HTTP {self.status_code}")
            err.response = self
            raise err


class TestGracefulDisable:
    """키가 없을 때 200 + available=False 여야 한다. 500이 아니다."""

    def test_translate_without_key(self, client, app):
        app.config["DEEPL_API_KEY"] = ""
        res = client.get("/api/translate?text=花に亡霊")
        assert res.status_code == 200
        assert res.get_json()["available"] is False

    def test_lyrics_without_source(self, client, app):
        app.config["KYSING_ENABLED"] = False
        res = client.get("/api/lyrics?title=花に亡霊&singer=ヨルシカ")
        assert res.status_code == 200
        body = res.get_json()
        assert body["available"] is False
        # 가사가 없어도 찾아갈 곳은 준다
        assert body["search_url"].startswith("https://www.google.com/search?q=")

    def test_no_network_call_without_key(self, app, monkeypatch):
        """키가 없으면 외부를 아예 부르지 않는다."""
        def boom(*a, **k):
            raise AssertionError("키가 없는데 외부를 호출했다")

        monkeypatch.setattr(requests, "post", boom)
        app.config["DEEPL_API_KEY"] = ""
        with app.app_context():
            assert translate.translate("花に亡霊")["available"] is False

    def test_health_reports_feature_flags(self, client, app):
        app.config["DEEPL_API_KEY"] = ""
        app.config["KYSING_ENABLED"] = True
        features = client.get("/api/health").get_json()["features"]
        assert features == {"translate": False, "lyrics": True, "preview": True}


class TestTranslate:
    def test_success(self, app, monkeypatch):
        monkeypatch.setattr(requests, "post", lambda *a, **k: FakeResponse(
            {"translations": [{"text": "꽃에 망령"}]}))
        app.config["DEEPL_API_KEY"] = "key:fx"
        with app.app_context():
            result = translate.translate("花に亡霊")
        assert result["available"] is True
        assert result["translated"] == "꽃에 망령"

    def test_free_key_uses_free_endpoint(self, app, monkeypatch):
        seen = {}

        def capture(url, **kwargs):
            seen["url"] = url
            return FakeResponse({"translations": [{"text": "x"}]})

        monkeypatch.setattr(requests, "post", capture)
        app.config["DEEPL_API_KEY"] = "abc:fx"
        with app.app_context():
            translate.translate("花")
        assert seen["url"] == translate.FREE_URL

    def test_pro_key_uses_pro_endpoint(self, app, monkeypatch):
        seen = {}
        monkeypatch.setattr(requests, "post", lambda url, **k: (
            seen.update(url=url), FakeResponse({"translations": [{"text": "x"}]}))[1])
        app.config["DEEPL_API_KEY"] = "abc"
        with app.app_context():
            translate.translate("花")
        assert seen["url"] == translate.PRO_URL

    def test_quota_exceeded_is_graceful(self, app, monkeypatch):
        monkeypatch.setattr(requests, "post", lambda *a, **k: FakeResponse({}, 456))
        app.config["DEEPL_API_KEY"] = "key:fx"
        with app.app_context():
            result = translate.translate("花")
        assert result["available"] is False
        assert "한도" in result["reason"]

    def test_upstream_error_is_graceful(self, app, monkeypatch):
        def boom(*a, **k):
            raise requests.ConnectionError("죽음")

        monkeypatch.setattr(requests, "post", boom)
        app.config["DEEPL_API_KEY"] = "key:fx"
        with app.app_context():
            assert translate.translate("花")["available"] is False

    def test_cached(self, app, monkeypatch, fake_redis):
        calls = []
        monkeypatch.setattr(requests, "post", lambda *a, **k: (
            calls.append(1), FakeResponse({"translations": [{"text": "번역"}]}))[1])
        app.config["DEEPL_API_KEY"] = "key:fx"
        with app.app_context():
            translate.translate("花に亡霊")
            second = translate.translate("花に亡霊")
        assert second["cached"] is True
        assert len(calls) == 1


class TestPreview:
    """iTunes Search는 키가 없어도 동작한다."""

    def test_picks_matching_track(self, app, monkeypatch):
        monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse({"results": [
            {"trackName": "엉뚱한곡", "artistName": "다른가수",
             "previewUrl": "https://x/1.m4a", "artworkUrl100": ""},
            {"trackName": "花に亡霊", "artistName": "ヨルシカ",
             "previewUrl": "https://x/2.m4a", "artworkUrl100": "a/100x100bb.jpg"},
        ]}))
        with app.app_context():
            result = preview.find("花に亡霊", "ヨルシカ")
        assert result["available"] is True
        assert result["preview_url"] == "https://x/2.m4a"

    def test_upgrades_artwork_size(self, app, monkeypatch):
        monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse({"results": [
            {"trackName": "花に亡霊", "artistName": "ヨルシカ",
             "previewUrl": "https://x/2.m4a", "artworkUrl100": "http://a/100x100bb.jpg"},
        ]}))
        with app.app_context():
            result = preview.find("花に亡霊", "ヨルシカ")
        assert result["artwork_url"] == "http://a/300x300bb.jpg"

    def test_rejects_unrelated_results(self, app, monkeypatch):
        """iTunes는 느슨하게 매칭하므로 엉뚱한 곡은 걸러야 한다."""
        monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse({"results": [
            {"trackName": "전혀다른곡", "artistName": "누구",
             "previewUrl": "https://x/9.m4a", "artworkUrl100": ""},
        ]}))
        with app.app_context():
            assert preview.find("花に亡霊", "ヨルシカ")["available"] is False

    def test_skips_entries_without_preview(self, app, monkeypatch):
        monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse({"results": [
            {"trackName": "花に亡霊", "artistName": "ヨルシカ", "artworkUrl100": ""},
        ]}))
        with app.app_context():
            assert preview.find("花に亡霊", "ヨルシカ")["available"] is False

    def test_upstream_error_is_graceful(self, app, monkeypatch):
        def boom(*a, **k):
            raise requests.Timeout("느림")

        monkeypatch.setattr(requests, "get", boom)
        with app.app_context():
            assert preview.find("花に亡霊")["available"] is False


def kysing_page(rows):
    """금영 검색 결과 HTML을 흉내 낸다. 첫 블록은 실제 사이트처럼 헤더다.

    rows: [(제목, 가수, [(한글발음, 후리가나, 원문), ...]), ...]
    """
    html = ['<ul class="search_chart_list clear"><li>헤더</li></ul>']
    for title, singer, lines in rows:
        body = "".join(
            f"{ko}<br />{ruby}<br />{ja}<br />" for ko, ruby, ja in lines
        )
        popup = (
            f'<div id="LyricsView" class="LyricsWrap clear">'
            f'<p class="LyricsClose">닫기</p>'
            f'<div class="LyricsCont"><p class="LyricsTit">{title}</p>{body}</div></div>'
            if lines
            else ""
        )
        html.append(
            '<ul class="search_chart_list clear">'
            "<li>♡</li><li>12345</li>"
            f'<li><span class="tit">{title}</span>'
            f'<span class="tit mo-art">{singer}</span>{popup}</li>'
            f"<li>{singer}</li><li>작곡</li><li>작사</li><li>2024.01</li>"
            "</ul>"
        )
    return "".join(html)


LINES = [
    ("모오 와스레테", "わす/", "もう忘れて"),
    ("시맛타카나", "", "しまったかな"),
]


class TestLyrics:
    """가사는 금영 검색 결과 HTML에 딸려 온다. 세 줄 묶음을 갈라 쓴다."""

    def test_success(self, app, monkeypatch):
        monkeypatch.setattr(kysing, "_fetch", lambda *a, **k: kysing_page(
            [("花に亡霊", "ヨルシカ", LINES)]))
        with app.app_context():
            result = lyrics.find("花に亡霊", "ヨルシカ")
        assert result["available"] is True
        assert result["provider"] == "금영"
        # 후리가나는 루비 위치가 빠져 있어 버리고, 발음과 원문만 남긴다
        assert result["lines"] == [
            {"ko": "모오 와스레테", "ja": "もう忘れて"},
            {"ko": "시맛타카나", "ja": "しまったかな"},
        ]

    def test_matches_title_ignoring_brackets(self, app, monkeypatch):
        """금영 제목에는 `("BEASTARS"OP)` 같은 꼬리표가 붙는다."""
        monkeypatch.setattr(kysing, "_fetch", lambda *a, **k: kysing_page(
            [('怪物 ("BEASTARS"OP)', "YOASOBI", LINES)]))
        with app.app_context():
            result = lyrics.find("怪物", "YOASOBI")
        assert result["available"] is True
        assert result["matched_title"] == '怪物 ("BEASTARS"OP)'

    def test_skips_other_songs_by_same_singer(self, app, monkeypatch):
        monkeypatch.setattr(kysing, "_fetch", lambda *a, **k: kysing_page([
            ("群青", "YOASOBI", [("군조오", "", "群青")]),
            ("夜に駆ける", "YOASOBI", LINES),
        ]))
        with app.app_context():
            result = lyrics.find("夜に駆ける", "YOASOBI")
        assert result["matched_title"] == "夜に駆ける"

    def test_intro_without_pronunciation_keeps_rest_aligned(self, app, monkeypatch):
        """'La la la' 도입부는 발음 줄이 없다. 여기서 밀리면 뒤가 통째로 어긋난다."""
        page = (
            '<ul class="search_chart_list clear"><li>헤더</li></ul>'
            '<ul class="search_chart_list clear"><li>♡</li><li>44684</li>'
            '<li><span class="tit">ミスター</span>'
            '<p class="LyricsClose">닫기</p>'
            '<div class="LyricsCont"><p class="LyricsTit">ミスター</p>'
            "La la la<br />"
            "싱그루 사이즈노 헤야데<br />//// へ/や /<br />シングルサイズの部屋で<br />"
            "</div></li>"
            "<li>YOASOBI</li><li>작곡</li><li>작사</li><li>2024.01</li></ul>"
        )
        monkeypatch.setattr(kysing, "_fetch", lambda *a, **k: page)
        with app.app_context():
            result = lyrics.find("ミスター", "YOASOBI")
        assert result["lines"] == [
            {"ko": "", "ja": "La la la"},
            {"ko": "싱그루 사이즈노 헤야데", "ja": "シングルサイズの部屋で"},
        ]

    def test_hiragana_only_line_is_not_mistaken_for_furigana(self, app, monkeypatch):
        """후리가나는 구분선이 있다. 그게 없으면 히라가나뿐이어도 가사 원문이다."""
        monkeypatch.setattr(kysing, "_fetch", lambda *a, **k: kysing_page(
            [("Pale Blue", "米津玄師", [("즛토 즛토", "", "ずっと ずっと")])]))
        with app.app_context():
            result = lyrics.find("Pale Blue", "米津玄師")
        assert result["lines"] == [{"ko": "즛토 즛토", "ja": "ずっと ずっと"}]

    def test_not_found_gives_search_link(self, app, monkeypatch):
        monkeypatch.setattr(kysing, "_fetch", lambda *a, **k: kysing_page([]))
        with app.app_context():
            result = lyrics.find("없는곡", "없는가수")
        assert result["available"] is False
        assert "%EC%97%86%EB%8A%94%EA%B3%A1" in result["search_url"]

    def test_upstream_error_is_graceful(self, app, monkeypatch):
        def boom(*a, **k):
            raise kysing.KysingError("죽음")

        monkeypatch.setattr(kysing, "_fetch", boom)
        with app.app_context():
            result = lyrics.find("花に亡霊", "ヨルシカ")
        assert result["available"] is False
        assert result["search_url"]

    def test_cached(self, app, monkeypatch, fake_redis):
        calls = []
        monkeypatch.setattr(kysing, "_fetch", lambda *a, **k: (
            calls.append(1), kysing_page([("花に亡霊", "ヨルシカ", LINES)]))[1])
        with app.app_context():
            lyrics.find("花に亡霊", "ヨルシカ")
            second = lyrics.find("花に亡霊", "ヨルシカ")
        assert second["cached"] is True
        assert second["available"] is True
        assert len(calls) == 1

    def test_lyrics_switch_does_not_touch_search(self, app, monkeypatch):
        """`LYRICS_ENABLED=false`는 가사만 끈다. 검색은 그대로 돌아야 한다.

        권리자가 가사만 안 된다고 할 때 쓰는 스위치다 (37번).
        `KYSING_ENABLED`를 내리면 금영 공식 검색까지 꺼져 최신곡이 사라진다.
        """
        def boom(*a, **k):
            raise AssertionError("가사가 꺼졌는데 금영을 호출했다")

        monkeypatch.setattr(kysing, "_fetch", boom)
        app.config["LYRICS_ENABLED"] = False
        with app.app_context():
            result = lyrics.find("花に亡霊", "ヨルシカ")
            assert result["available"] is False
            assert result["search_url"]
            # 검색 쪽 스위치는 건드리지 않았다
            assert app.config["KYSING_ENABLED"] is True


class TestValidation:
    @pytest.mark.parametrize("path", [
        "/api/translate?text=",
        "/api/preview?title=",
        "/api/lyrics?title=",
    ])
    def test_empty_input_is_graceful(self, client, path, app):
        app.config["DEEPL_API_KEY"] = "k"
        res = client.get(path)
        assert res.status_code == 200
        assert res.get_json()["available"] is False


class TestCacheNamespace:
    """검색 캐시와 부가 기능 캐시가 이름 공간을 나눠 써야 한다."""

    def test_lyrics_search_and_lyrics_lookup_do_not_collide(self, app):
        """`type=lyrics` 검색과 `/api/lyrics` 조회는 셋 다 3토막이라 겹칠 수 있었다.

        `lyrics:all:yoasobi`가 "brand=all에서 yoasobi 가사 검색"이면서
        동시에 "ALL(곡)/YOASOBI의 가사"로 읽혔다.
        """
        with app.app_context():
            search = _cache_key("YOASOBI", "lyrics", "all")
            lookup = cache.make_key(
                "lyrics", normalize_text("ALL"), normalize_text("YOASOBI")
            )
        assert search != lookup

    def test_search_keys_are_namespaced(self, app):
        with app.app_context():
            assert _cache_key("花", "song", "tj").startswith(f"{cache.CACHE_PREFIX}:q2:")


class TestLyricsLookupResilience:
    def test_retries_when_first_page_comes_back_empty(self, app, monkeypatch):
        """금영은 부하가 걸리면 빈 페이지를 간헐적으로 준다.

        이걸 진짜 0건으로 받아들이면 '가사 없음'이 하루 동안 캐시된다.
        """
        pages = ["", kysing_page([("花に亡霊", "ヨルシカ", LINES)])]
        monkeypatch.setattr(kysing, "_fetch", lambda *a, **k: pages.pop(0))
        with app.app_context():
            result = lyrics.find("花に亡霊", "ヨルシカ")
        assert result["available"] is True
        assert pages == []
