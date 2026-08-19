import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """공통 설정."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    # MySQL
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "karaokedayo")
    MYSQL_POOL_SIZE = int(os.getenv("MYSQL_POOL_SIZE", 8))
    MYSQL_TIMEOUT = float(os.getenv("MYSQL_TIMEOUT", 5))
    # 자체 DB를 검색에 쓸지. 끄면 예전처럼 매번 외부 사이트를 본다.
    DB_SEARCH_ENABLED = os.getenv("DB_SEARCH_ENABLED", "true").lower() != "false"

    # Redis
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))
    # manana API가 하루 1회 갱신되므로 기본 24시간
    CACHE_TTL = int(os.getenv("CACHE_TTL", 86400))

    # manana 비공식 노래방 API
    MANANA_BASE_URL = os.getenv("MANANA_BASE_URL", "https://api.manana.kr")
    MANANA_TIMEOUT = float(os.getenv("MANANA_TIMEOUT", 8))

    # 금영 공식 사이트 스크래핑.
    # manana의 금영 데이터가 멈춰 있어 최신곡을 여기서 보완한다.
    # 끄면 manana만 쓴다 (폴백과 동일한 동작).
    KYSING_ENABLED = os.getenv("KYSING_ENABLED", "true").lower() != "false"
    KYSING_TIMEOUT = float(os.getenv("KYSING_TIMEOUT", 10))
    # 가사 검색은 금영 서버가 느리다 (실측 11초). 넉넉히 잡는다.
    KYSING_LYRICS_TIMEOUT = float(os.getenv("KYSING_LYRICS_TIMEOUT", 25))

    # TJ 공식 사이트 스크래핑.
    # manana에는 한글 발음 검색이 없어서 공식을 먼저 본다.
    TJMEDIA_ENABLED = os.getenv("TJMEDIA_ENABLED", "true").lower() != "false"
    TJMEDIA_TIMEOUT = float(os.getenv("TJMEDIA_TIMEOUT", 10))

    # 부가 기능. 키가 없으면 해당 기능만 꺼지고 검색은 그대로 동작한다.
    DEEPL_API_KEY = os.getenv("DEEPL_API_KEY", "")
    DEEPL_TIMEOUT = float(os.getenv("DEEPL_TIMEOUT", 8))

    # 가사는 금영 검색 결과에 딸려 오므로 KYSING_ENABLED를 따른다. 별도 키가 없다.
    # 권리 확인은 진행 중이다 — DECISIONS.md 37번.
    #
    # 가사만 따로 끄는 스위치. 권리자가 안 된다고 하면 이것만 내리면 된다.
    # KYSING_ENABLED를 내리면 금영 공식 '검색'까지 같이 꺼진다(manana 폴백).
    LYRICS_ENABLED = os.getenv("LYRICS_ENABLED", "true").lower() != "false"

    # 미리듣기는 iTunes Search API를 쓴다. 키가 필요 없어 항상 켜져 있다.
    ITUNES_TIMEOUT = float(os.getenv("ITUNES_TIMEOUT", 8))

    # 세션 쿠키. 자바스크립트가 못 읽게 하고(XSS 방어),
    # 배포 시에는 HTTPS에서만 전송되도록 SESSION_COOKIE_SECURE를 켠다.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    PERMANENT_SESSION_LIFETIME = int(os.getenv("SESSION_LIFETIME", 60 * 60 * 24 * 14))

    # bcrypt 작업 계수. 높을수록 안전하지만 로그인이 느려진다.
    BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", 12))

    # 프로필 이미지 data URL 상한 (base64라 원본보다 약 1.4배)
    AVATAR_MAX_BYTES = int(os.getenv("AVATAR_MAX_BYTES", 400 * 1024))

    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    # 운영에서는 HTTPS를 전제로 한다. 안 그러면 세션 쿠키가 평문으로 오간다.
    SESSION_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}


def get_config():
    return config_by_name.get(os.getenv("FLASK_ENV", "development"), DevelopmentConfig)
