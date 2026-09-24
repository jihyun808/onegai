import pytest

from app.models import user
from app.services import auth_service
from app.services.auth_service import AuthError


@pytest.fixture
def fake_users(monkeypatch):

    class Store:
        def __init__(self):
            self.rows = {}
            self.next_id = 1

        def find_by_username(self, username):
            return self.rows.get(username.lower())

        def exists(self, username):
            return username.lower() in self.rows

        def get(self, user_id):
            for row in self.rows.values():
                if row["id"] == user_id:
                    return {
                        "id": row["id"],
                        "username": row["username"],
                        "avatar": row["avatar"],
                    }
            return None

        def create(self, username, password_hash):
            key = username.lower()
            if key in self.rows:
                return None
            row = {
                "id": self.next_id,
                "username": username,
                "password_hash": password_hash,
                "avatar": None,
            }
            self.rows[key] = row
            self.next_id += 1
            return {"id": row["id"], "username": username, "avatar": None}

    store = Store()
    monkeypatch.setattr(user, "find_by_username", store.find_by_username)
    monkeypatch.setattr(user, "exists", store.exists)
    monkeypatch.setattr(user, "create", store.create)
    monkeypatch.setattr(user, "get", store.get)
    return store


class TestPasswordHashing:
    def test_never_stores_plaintext(self, app, fake_users):
        with app.app_context():
            auth_service.register("jihyeon", "password123")

        stored = fake_users.rows["jihyeon"]["password_hash"]
        assert "password123" not in stored
        assert stored.startswith("$2b$"), "bcrypt 해시여야 한다"

    def test_same_password_gets_different_hashes(self, app, fake_users):
        with app.app_context():
            a = auth_service.hash_password("password123")
            b = auth_service.hash_password("password123")
        assert a != b
        assert auth_service.verify_password("password123", a)
        assert auth_service.verify_password("password123", b)

    def test_broken_hash_is_not_a_crash(self, app):
        with app.app_context():
            assert auth_service.verify_password("x", "쓰레기값") is False


class TestRegister:
    def test_rejects_short_password(self, app, fake_users):
        with app.app_context(), pytest.raises(AuthError) as caught:
            auth_service.register("jihyeon", "1234")
        assert caught.value.field == "password"

    def test_rejects_duplicate_username(self, app, fake_users):
        with app.app_context():
            auth_service.register("jihyeon", "password123")
            with pytest.raises(AuthError) as caught:
                auth_service.register("jihyeon", "another123")

        assert caught.value.field == "username"
        assert "중복" in str(caught.value)

    def test_duplicate_check_ignores_case(self, app, fake_users):
        with app.app_context():
            auth_service.register("jihyeon", "password123")
            with pytest.raises(AuthError):
                auth_service.register("JIHYEON", "password123")

    @pytest.mark.parametrize("name", ["ab", "a" * 21, "have space", "한글아이디"])
    def test_rejects_bad_username(self, app, fake_users, name):
        with app.app_context(), pytest.raises(AuthError) as caught:
            auth_service.register(name, "password123")
        assert caught.value.field == "username"

    def test_allows_long_passphrase(self, app, fake_users):
        with app.app_context():
            created = auth_service.register("jihyeon", "correct horse battery staple")
        assert created["username"] == "jihyeon"


class TestLogin:
    def test_success(self, app, fake_users, fake_redis):
        with app.app_context():
            auth_service.register("jihyeon", "password123")
            found = auth_service.login("jihyeon", "password123")
        assert found["username"] == "jihyeon"

    def test_unknown_user_and_wrong_password_look_alike(self, app, fake_users, fake_redis):
        with app.app_context():
            auth_service.register("jihyeon", "password123")

            with pytest.raises(AuthError) as wrong:
                auth_service.login("jihyeon", "wrongpass1")
            with pytest.raises(AuthError) as missing:
                auth_service.login("nobodyhere", "wrongpass1")

        assert "맞지 않아요" in str(wrong.value)
        assert "맞지 않아요" in str(missing.value)

    def test_locks_after_five_failures(self, app, fake_users, fake_redis):
        with app.app_context():
            auth_service.register("jihyeon", "password123")

            for _ in range(auth_service.MAX_ATTEMPTS):
                with pytest.raises(AuthError):
                    auth_service.login("jihyeon", "wrongpass1")

            with pytest.raises(AuthError) as caught:
                auth_service.login("jihyeon", "password123")

        assert "5번 틀렸어요" in str(caught.value)

    def test_success_clears_counter(self, app, fake_users, fake_redis):
        with app.app_context():
            auth_service.register("jihyeon", "password123")
            for _ in range(3):
                with pytest.raises(AuthError):
                    auth_service.login("jihyeon", "wrongpass1")

            auth_service.login("jihyeon", "password123")
            assert auth_service.attempts_left("jihyeon") == auth_service.MAX_ATTEMPTS


class TestEndpoints:
    def test_register_sets_session_cookie(self, client, fake_users):
        res = client.post(
            "/api/auth/register", json={"username": "jihyeon", "password": "password123"}
        )
        assert res.status_code == 201

        cookie = res.headers.get("Set-Cookie", "")
        assert "HttpOnly" in cookie, "세션 쿠키는 자바스크립트가 못 읽어야 한다"

    def test_me_returns_null_when_logged_out(self, client, fake_users):
        assert client.get("/api/auth/me").get_json() is None

    def test_me_after_register(self, client, fake_users):
        client.post(
            "/api/auth/register", json={"username": "jihyeon", "password": "password123"}
        )
        assert client.get("/api/auth/me").get_json()["username"] == "jihyeon"

    def test_logout_clears_session(self, client, fake_users):
        client.post(
            "/api/auth/register", json={"username": "jihyeon", "password": "password123"}
        )
        client.post("/api/auth/logout")
        assert client.get("/api/auth/me").get_json() is None

    def test_error_carries_field(self, client, fake_users):
        res = client.post(
            "/api/auth/register", json={"username": "jihyeon", "password": "1234"}
        )
        assert res.status_code == 400
        assert res.get_json()["field"] == "password"

    def test_patch_me_requires_login(self, client, fake_users):
        assert client.patch("/api/auth/me", json={"username": "other"}).status_code == 401


class TestRateLimit:

    def test_blocks_burst_of_signups(self, client, fake_users, fake_redis):
        codes = []
        for i in range(12):
            res = client.post(
                "/api/auth/register",
                json={"username": f"user{i:04d}", "password": "password123"},
            )
            codes.append(res.status_code)

        assert 429 in codes, "무더기 가입이 막혀야 한다"
        assert codes.count(429) >= 2

    def test_sends_retry_after(self, client, fake_users, fake_redis):
        for i in range(12):
            res = client.post(
                "/api/auth/register",
                json={"username": f"user{i:04d}", "password": "password123"},
            )
        assert res.status_code == 429
        assert res.headers.get("Retry-After")

    def test_login_burst_across_accounts(self, client, fake_users, fake_redis):
        codes = []
        for i in range(25):
            res = client.post(
                "/api/auth/login",
                json={"username": f"someone{i:03d}", "password": "guessing123"},
            )
            codes.append(res.status_code)

        assert 429 in codes

    def test_passes_through_without_redis(self, client, fake_users):
        codes = []
        for i in range(15):
            res = client.post(
                "/api/auth/register",
                json={"username": f"user{i:04d}", "password": "password123"},
            )
            codes.append(res.status_code)

        assert 429 not in codes


class TestAccessLog:

    @pytest.fixture
    def logged(self, monkeypatch):
        from app.models import access_log

        rows = []
        monkeypatch.setattr(
            access_log, "record",
            lambda user_id, action, ip, status: rows.append((user_id, action, status)),
        )
        return rows

    def test_records_auth_request(self, client, logged):
        client.post("/api/auth/login", json={"username": "없는사람", "password": "x"})

        assert any(a == "POST /api/auth/login" for _, a, _ in logged)

    def test_records_favorites_request(self, client, logged):
        client.get("/api/favorites")

        assert any(a == "GET /api/favorites" for _, a, _ in logged)

    def test_search_is_not_recorded(self, client, logged):
        client.get("/api/search?q=ヨルシカ")

        assert logged == []

    def test_failure_to_log_does_not_break_request(self, client, monkeypatch):
        from app.utils import db

        def boom(*a, **k):
            raise RuntimeError("DB 다운")

        monkeypatch.setattr(db, "execute_many", boom)
        assert client.get("/api/favorites").status_code in (200, 401)
