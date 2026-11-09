import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, g, render_template, request
from flask_wtf.csrf import CSRFError, CSRFProtect
from sqlalchemy.orm import Session

from .config import database_engine
from .profile_photo import MAX_PHOTO_BYTES


def create_app():
    load_dotenv()
    app = Flask(__name__)
    secret = os.environ.get("SECRET_KEY", "")
    if len(secret) < 32:
        raise RuntimeError("Configura SECRET_KEY con al menos 32 caracteres aleatorios.")
    app.config.update(
        SECRET_KEY=secret,
        SESSION_COOKIE_SECURE=os.environ.get("LATIA_SECURE_COOKIES", "1") != "0",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
        MAX_CONTENT_LENGTH=64 * 1024,
    )
    @app.before_request
    def allow_photo_upload():
        if request.endpoint == "journal.upload_photo":
            request.max_content_length = MAX_PHOTO_BYTES + 64 * 1024

    CSRFProtect(app)
    app.extensions["latia_engine"] = database_engine()

    @app.teardown_appcontext
    def close_session(_error):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.after_request
    def privacy_headers(response):
        if not response.mimetype.startswith(("text/css", "application/javascript")):
            response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @app.errorhandler(CSRFError)
    def invalid_form(_error):
        return render_template("error.html", message="La sesión del formulario venció. Vuelve a abrir la página e inténtalo de nuevo."), 400

    @app.errorhandler(413)
    def request_too_large(_error):
        message = "La foto debe pesar como máximo 5 MB." if request.endpoint == "journal.upload_photo" else "El formulario supera el tamaño permitido."
        return render_template("error.html", message=message), 413

    from .views import journal, create_user

    app.register_blueprint(journal)
    app.cli.add_command(create_user)
    return app


def database():
    from flask import current_app

    if "db" not in g:
        g.db = Session(current_app.extensions["latia_engine"])
    return g.db
