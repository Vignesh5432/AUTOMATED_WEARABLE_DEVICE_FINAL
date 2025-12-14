"""Flask application factory for Industrial Worker Safety Monitoring."""

from __future__ import annotations

import logging
from flask import Flask, render_template

import config
from backend.db import db, bcrypt, init_db
from backend.auth import auth_bp
from backend.routes_worker import worker_bp
from backend.routes_admin import admin_bp
from backend.routes_ui import ui_bp


def create_app():
    app = Flask(__name__, static_folder="../static", template_folder="../templates")
    app.config.from_object(config)
    db.init_app(app)
    bcrypt.init_app(app)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    with app.app_context():
        init_db()
    app.register_blueprint(auth_bp)
    app.register_blueprint(worker_bp, url_prefix="/worker")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(ui_bp)

    # Log helpful URLs immediately (Flask 3 removed before_first_request)
    logging.info("Worker UI: http://localhost:5000/")
    logging.info("Admin UI:  http://localhost:5000/admin")

    return app


# For flask run
app = create_app()


@app.route("/healthz")
def healthz():
    return {"status": "ok"}



