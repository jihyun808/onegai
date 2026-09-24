import os

from dotenv import load_dotenv

load_dotenv()


class Config:

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "karaokedayo")
    MYSQL_POOL_SIZE = int(os.getenv("MYSQL_POOL_SIZE", 8))
    MYSQL_TIMEOUT = float(os.getenv("MYSQL_TIMEOUT", 5))
    DB_SEARCH_ENABLED = os.getenv("DB_SEARCH_ENABLED", "true").lower() != "false"

    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD") or None
    CACHE_TTL = int(os.getenv("CACHE_TTL", 86400))

    MANANA_BASE_URL = os.getenv("MANANA_BASE_URL", "https://api.manana.kr")
    MANANA_TIMEOUT = float(os.getenv("MANANA_TIMEOUT", 8))

    KYSING_ENABLED = os.getenv("KYSING_ENABLED", "true").lower() != "false"
    KYSING_TIMEOUT = float(os.getenv("KYSING_TIMEOUT", 10))
    KYSING_LYRICS_TIMEOUT = float(os.getenv("KYSING_LYRICS_TIMEOUT", 25))

    TJMEDIA_ENABLED = os.getenv("TJMEDIA_ENABLED", "true").lower() != "false"
    TJMEDIA_TIMEOUT = float(os.getenv("TJMEDIA_TIMEOUT", 10))

    DEEPL_API_KEY = os.getenv("DEEPL_API_KEY", "")
    DEEPL_TIMEOUT = float(os.getenv("DEEPL_TIMEOUT", 8))

    LYRICS_ENABLED = os.getenv("LYRICS_ENABLED", "true").lower() != "false"

    ITUNES_TIMEOUT = float(os.getenv("ITUNES_TIMEOUT", 8))

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    PERMANENT_SESSION_LIFETIME = int(os.getenv("SESSION_LIFETIME", 60 * 60 * 24 * 14))

    BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", 12))

    AVATAR_MAX_BYTES = int(os.getenv("AVATAR_MAX_BYTES", 400 * 1024))

    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}


def get_config():
    return config_by_name.get(os.getenv("FLASK_ENV", "development"), DevelopmentConfig)
