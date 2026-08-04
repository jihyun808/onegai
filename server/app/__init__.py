from flask import Flask
from flask_cors import CORS

from config import get_config


def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())

    # 한글/일본어를 \uXXXX 로 이스케이프하지 않는다. 응답 크기가 줄고 로그도 읽힌다.
    app.json.ensure_ascii = False

    CORS(app, origins=app.config["CORS_ORIGINS"])

    from app.cli import register_cli
    from app.routes import register_routes

    register_routes(app)
    register_cli(app)

    return app
