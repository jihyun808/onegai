def register_routes(app):
    from app.routes import auth, extras, favorites, health, search

    app.register_blueprint(health.bp)
    app.register_blueprint(search.bp)
    app.register_blueprint(extras.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(favorites.bp)
