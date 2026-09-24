import pytest

from app import create_app
from app.utils import cache


class FakeRedis:

    def __init__(self):
        self.store = {}
        self.ttls = {}

    def ping(self):
        return True

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value
        self.ttls[key] = ttl

    def delete(self, key):
        self.store.pop(key, None)
        self.ttls.pop(key, None)

    def incr(self, key):
        value = int(self.store.get(key, 0)) + 1
        self.store[key] = value
        return value

    def expire(self, key, ttl):
        self.ttls[key] = ttl

    def ttl(self, key):
        return self.ttls.get(key, -1)


@pytest.fixture
def app():
    application = create_app()
    application.config.update(TESTING=True, BCRYPT_ROUNDS=4)
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch):

    from app.services import kysing, tjmedia

    def blocked(keyword, search_type="song"):
        return []

    monkeypatch.setattr(kysing, "search", blocked)
    monkeypatch.setattr(tjmedia, "search", blocked)

    from app.utils import db

    db.reset_pool()
    monkeypatch.setattr(db, "get_pool", lambda: None)


@pytest.fixture(autouse=True)
def no_real_redis(monkeypatch):
    cache.reset_client()
    monkeypatch.setattr(cache, "get_client", lambda: None)
    yield
    cache.reset_client()


@pytest.fixture
def fake_redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(cache, "get_client", lambda: fake)
    return fake


@pytest.fixture
def fake_manana(monkeypatch):

    from app.services import manana

    class Recorder:
        def __init__(self):
            self.calls = []
            self.by_brand = {}
            self.error = None

        def search(self, keyword, search_type="song", brand=None):
            self.calls.append((search_type, keyword, brand))
            if self.error:
                raise self.error
            return list(self.by_brand.get(brand, []))

    recorder = Recorder()
    monkeypatch.setattr(manana, "search", recorder.search)
    return recorder


def entry(brand, no, title, singer, release="2026-01-01"):
    return {
        "brand": brand,
        "no": no,
        "title": title,
        "singer": singer,
        "composer": "",
        "lyricist": "",
        "release": release,
    }


def _scraper_recorder(monkeypatch, module):
    class Recorder:
        def __init__(self):
            self.calls = []
            self.rows = []
            self.error = None

        def search(self, keyword, search_type="song"):
            self.calls.append((search_type, keyword))
            if self.error:
                raise self.error
            return list(self.rows)

    recorder = Recorder()
    monkeypatch.setattr(module, "search", recorder.search)
    return recorder


@pytest.fixture
def fake_tjmedia(monkeypatch):
    from app.services import tjmedia

    return _scraper_recorder(monkeypatch, tjmedia)


@pytest.fixture
def fake_kysing(monkeypatch):
    from app.services import kysing

    class Recorder:
        def __init__(self):
            self.calls = []
            self.rows = []
            self.error = None

        def search(self, keyword, search_type="song"):
            self.calls.append((search_type, keyword))
            if self.error:
                raise self.error
            return list(self.rows)

    recorder = Recorder()
    monkeypatch.setattr(kysing, "search", recorder.search)
    return recorder
