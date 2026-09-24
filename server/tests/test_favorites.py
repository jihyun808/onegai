import pytest

from app.models import favorite
from app.routes.auth import SESSION_KEY


@pytest.fixture
def fake_favorites(monkeypatch):

    class Store:
        def __init__(self):
            self.rows = {}

        def list_for(self, user_id):
            return [
                {**row, "created_at": None}
                for (uid, _, _), row in self.rows.items()
                if uid == user_id
            ]

        def add_many(self, user_id, entries):
            saved = 0
            for e in entries:
                key = (user_id, e["brand"], e["no"])
                if key in self.rows:
                    continue
                self.rows[key] = {
                    "brand": e["brand"],
                    "no": e["no"],
                    "title": e.get("title", ""),
                    "singer": e.get("singer", ""),
                }
                saved += 1
            return saved

        def remove(self, user_id, brand, song_no):
            return 1 if self.rows.pop((user_id, brand, song_no), None) else 0

    store = Store()
    monkeypatch.setattr(favorite, "list_for", store.list_for)
    monkeypatch.setattr(favorite, "add_many", store.add_many)
    monkeypatch.setattr(favorite, "remove", store.remove)
    return store


@pytest.fixture
def logged_in(client):
    with client.session_transaction() as sess:
        sess[SESSION_KEY] = 1
    return client


SONGS = [
    {"brand": "tj", "no": "68381", "title": "夜に駆ける", "singer": "YOASOBI"},
    {"brand": "kumyoung", "no": "44656", "title": "夜に駆ける", "singer": "YOASOBI"},
]


class TestAuthRequired:
    def test_list_requires_login(self, client, fake_favorites):
        assert client.get("/api/favorites").status_code == 401

    def test_add_requires_login(self, client, fake_favorites):
        assert client.post("/api/favorites", json={"songs": SONGS}).status_code == 401

    def test_delete_requires_login(self, client, fake_favorites):
        assert client.delete("/api/favorites/tj/68381").status_code == 401


class TestFavorites:
    def test_add_and_list(self, logged_in, fake_favorites):
        res = logged_in.post("/api/favorites", json={"songs": SONGS})
        assert res.status_code == 201
        assert res.get_json()["saved"] == 2

        body = logged_in.get("/api/favorites").get_json()
        assert body["total"] == 2

    def test_both_brands_become_one_card(self, logged_in, fake_favorites):
        logged_in.post("/api/favorites", json={"songs": SONGS})
        groups = logged_in.get("/api/favorites").get_json()["groups"]

        assert len(groups) == 1
        assert groups[0]["both"] is True
        assert groups[0]["brands"] == {"tj": ["68381"], "kumyoung": ["44656"]}

    def test_duplicate_is_ignored(self, logged_in, fake_favorites):
        logged_in.post("/api/favorites", json={"songs": SONGS})
        again = logged_in.post("/api/favorites", json={"songs": SONGS})

        assert again.get_json()["saved"] == 0
        assert logged_in.get("/api/favorites").get_json()["total"] == 2

    def test_remove_one_brand_keeps_other(self, logged_in, fake_favorites):
        logged_in.post("/api/favorites", json={"songs": SONGS})
        logged_in.delete("/api/favorites/tj/68381")

        groups = logged_in.get("/api/favorites").get_json()["groups"]
        assert groups[0]["brands"] == {"kumyoung": ["44656"]}
        assert groups[0]["both"] is False

    def test_empty_payload_rejected(self, logged_in, fake_favorites):
        assert logged_in.post("/api/favorites", json={"songs": []}).status_code == 400

    def test_bulk_is_capped(self, logged_in, fake_favorites):
        from app.routes.favorites import MAX_BULK

        many = [
            {"brand": "tj", "no": str(i), "title": f"곡{i}", "singer": "가수"}
            for i in range(MAX_BULK + 50)
        ]
        res = logged_in.post("/api/favorites", json={"songs": many})
        assert res.get_json()["saved"] == MAX_BULK

    def test_db_outage_returns_503(self, logged_in, monkeypatch):
        monkeypatch.setattr(favorite, "list_for", lambda user_id: None)
        assert logged_in.get("/api/favorites").status_code == 503
