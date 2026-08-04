"""번역 · 미리듣기 · 가사. 핵심은 '키가 없어도 안 터진다'."""

import pytest
import requests

from app.services import lyrics, preview, translate


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

    def test_lyrics_without_key(self, client, app):
        app.config["MUSIXMATCH_API_KEY"] = ""
        res = client.get("/api/lyrics?title=花に亡霊&singer=ヨルシカ")
        assert res.status_code == 200
        assert res.get_json()["available"] is False

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
        app.config["MUSIXMATCH_API_KEY"] = "x"
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


class TestLyrics:
    def _payload(self, status=200, body=None):
        return {"message": {"header": {"status_code": status}, "body": body or {}}}

    def test_success(self, app, monkeypatch):
        monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(self._payload(
            body={"lyrics": {"lyrics_body": "가사 본문\n\n***\n상업적 이용 금지",
                             "script_tracking_url": "http://t"}})))
        app.config["MUSIXMATCH_API_KEY"] = "k"
        with app.app_context():
            result = lyrics.find("花に亡霊", "ヨルシカ")
        assert result["available"] is True
        # 저작권 문구는 본문에서 떼어낸다
        assert result["lyrics"] == "가사 본문"
        assert result["partial"] is True

    def test_nested_401_is_graceful(self, app, monkeypatch):
        """Musixmatch는 오류일 때도 HTTP 200을 준다. 본문의 코드를 봐야 한다."""
        monkeypatch.setattr(requests, "get",
                            lambda *a, **k: FakeResponse(self._payload(401)))
        app.config["MUSIXMATCH_API_KEY"] = "bad"
        with app.app_context():
            assert lyrics.find("花", "ヨルシカ")["available"] is False

    def test_quota_exceeded(self, app, monkeypatch):
        monkeypatch.setattr(requests, "get",
                            lambda *a, **k: FakeResponse(self._payload(402)))
        app.config["MUSIXMATCH_API_KEY"] = "k"
        with app.app_context():
            assert "한도" in lyrics.find("花", "ヨルシカ")["reason"]

    def test_not_found(self, app, monkeypatch):
        monkeypatch.setattr(requests, "get",
                            lambda *a, **k: FakeResponse(self._payload(404)))
        app.config["MUSIXMATCH_API_KEY"] = "k"
        with app.app_context():
            assert lyrics.find("없는곡", "없는가수")["available"] is False


class TestValidation:
    @pytest.mark.parametrize("path", [
        "/api/translate?text=",
        "/api/preview?title=",
        "/api/lyrics?title=",
    ])
    def test_empty_input_is_graceful(self, client, path, app):
        app.config["DEEPL_API_KEY"] = "k"
        app.config["MUSIXMATCH_API_KEY"] = "k"
        res = client.get(path)
        assert res.status_code == 200
        assert res.get_json()["available"] is False
