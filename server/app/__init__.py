from flask import Flask
from flask_cors import CORS

from config import get_config


def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())

    # 한글/일본어를 \uXXXX 로 이스케이프하지 않는다. 응답 크기가 줄고 로그도 읽힌다.
    app.json.ensure_ascii = False

    # 세션 쿠키를 주고받아야 하므로 credentials를 허용한다.
    # 이때 origins에 '*'를 쓰면 안 된다(브라우저가 거부한다).
    CORS(app, origins=app.config["CORS_ORIGINS"], supports_credentials=True)

    from app.cli import register_cli
    from app.routes import register_routes

    register_routes(app)
    register_cli(app)

    return app
