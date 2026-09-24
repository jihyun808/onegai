import pytest

from app import create_app
from app.utils import cache


class FakeRedis:
    """테스트용 인메모리 Redis. TTL은 저장만 하고 만료시키지는 않는다."""

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
    # bcrypt 기본값(12)은 해시 한 번에 0.3초라 테스트가 느려진다.
    # 알고리즘은 그대로이므로 검증 의미는 유지된다.
    application.config.update(TESTING=True, BCRYPT_ROUNDS=4)
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch):
    """테스트가 실제 외부 사이트를 치지 않게 막는다.

    금영 공식 스크래퍼는 기본적으로 빈 결과를 내도록 해 둔다.
    그러면 폴백이 동작해 manana(fake_manana)가 쓰이므로,
    소스 선택을 신경 쓰지 않는 테스트는 예전 그대로 동작한다.
    """
    from app.services import kysing, tjmedia

    def blocked(keyword, search_type="song"):
        return []

    monkeypatch.setattr(kysing, "search", blocked)
    monkeypatch.setattr(tjmedia, "search", blocked)

    # 실제 MySQL도 건드리지 않는다. 테스트가 개발 DB를 바꾸면 안 된다.
    from app.utils import db

    db.reset_pool()
    monkeypatch.setattr(db, "get_pool", lambda: None)


@pytest.fixture(autouse=True)
def no_real_redis(monkeypatch):
    """테스트가 실제 Redis를 건드리지 않도록 기본값은 캐시 비활성."""
    cache.reset_client()
    monkeypatch.setattr(cache, "get_client", lambda: None)
    yield
    cache.reset_client()


@pytest.fixture
def fake_redis(monkeypatch):
    """캐시 동작을 검증할 때 쓰는 인메모리 Redis."""
    fake = FakeRedis()
    monkeypatch.setattr(cache, "get_client", lambda: fake)
    return fake


@pytest.fixture
def fake_manana(monkeypatch):
    """manana API 호출을 가로챈다. 네트워크를 타지 않는다.

    calls 에 (search_type, keyword, brand) 가 쌓인다.
    """
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
    """TJ 공식 스크래퍼를 가로챈다."""
    from app.services import tjmedia

    return _scraper_recorder(monkeypatch, tjmedia)


@pytest.fixture
def fake_kysing(monkeypatch):
    """금영 공식 스크래퍼를 가로챈다. 네트워크를 타지 않는다."""
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
