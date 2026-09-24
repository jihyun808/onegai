from flask import Flask, request, session
from flask_cors import CORS

from config import get_config


def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())

    # 기본 키로 운영에 뜨면 누구나 세션 쿠키를 위조할 수 있다. 아예 안 뜨게 막는다.
    if not app.config["DEBUG"] and app.config["SECRET_KEY"] == "dev-secret-key":
        raise RuntimeError("운영 환경에서는 SECRET_KEY를 반드시 설정해야 합니다.")

    # 한글/일본어를 \uXXXX 로 이스케이프하지 않는다. 응답 크기가 줄고 로그도 읽힌다.
    app.json.ensure_ascii = False

    # 세션 쿠키를 주고받아야 하므로 credentials를 허용한다.
    # 이때 origins에 '*'를 쓰면 안 된다(브라우저가 거부한다).
    CORS(app, origins=app.config["CORS_ORIGINS"], supports_credentials=True)

    from app.cli import register_cli
    from app.routes import register_routes

    register_routes(app)
    register_cli(app)
    _log_personal_data_access(app)

    return app


# 개인정보를 다루는 경로. 이 아래 요청만 접속기록에 남긴다.
# 곡 검색은 개인정보와 무관하고, 남기면 오히려 취향 기록이 쌓인다.
_PERSONAL_PREFIXES = ("/api/auth", "/api/favorites")


def _log_personal_data_access(app):
    """개인정보처리시스템 접속기록을 남긴다.

    「개인정보의 안전성 확보조치 기준」 제8조. 라우트마다 호출을 흩뿌리지
    않고 한곳에서 처리한다 — 빠뜨린 경로가 생기면 기록에 구멍이 난다.

    응답이 나간 뒤에 남기므로 결과(status)까지 함께 적힌다.
    """
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
