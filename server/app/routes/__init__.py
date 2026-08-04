def register_routes(app):
    """블루프린트 등록 위치. 라우트 추가 시 여기에 연결한다."""
    from app.routes import extras, health, search

    app.register_blueprint(health.bp)
    app.register_blueprint(search.bp)
    app.register_blueprint(extras.bp)
