from flask import Flask, request, session
from flask_cors import CORS

from config import get_config


def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())

    if not app.config["DEBUG"] and app.config["SECRET_KEY"] == "dev-secret-key":
        raise RuntimeError("운영 환경에서는 SECRET_KEY를 반드시 설정해야 합니다.")

    app.json.ensure_ascii = False

    CORS(app, origins=app.config["CORS_ORIGINS"], supports_credentials=True)

    from app.cli import register_cli
    from app.routes import register_routes

    register_routes(app)
    register_cli(app)
    _log_personal_data_access(app)

    return app


_PERSONAL_PREFIXES = ("/api/auth", "/api/favorites")


def _log_personal_data_access(app):


    from app.models import access_log
    from app.routes.auth import SESSION_KEY
    from app.utils.ratelimit import client_ip

    @app.after_request
    def write_access_log(response):
        if request.path.startswith(_PERSONAL_PREFIXES):
            access_log.record(
                session.get(SESSION_KEY),
                f"{request.method} {request.path}",
                client_ip(),
                response.status_code,
            )
        return response
