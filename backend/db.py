"""Database setup and initialization helpers."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy

import config

db = SQLAlchemy()
bcrypt = Bcrypt()


def init_db():
    """Create tables and seed an admin + demo worker if DB not present."""
    db.create_all()
    from backend.models import User, Worker  # noqa: WPS433

    # Seed admin
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", role="admin", password_hash=bcrypt.generate_password_hash("admin123").decode())
        db.session.add(admin)

    # Seed demo worker
    if not Worker.query.filter_by(worker_id="W-001").first():
        w = Worker(worker_id="W-001", name="Demo Worker", zone="NORMAL", last_seen=dt.datetime.utcnow())
        db.session.add(w)

    # Seed worker user with PIN 1234
    if not User.query.filter_by(worker_id="W-001", role="worker").first():
        user = User(
            username="worker1",
            role="worker",
            worker_id="W-001",
            pin="1234",
            password_hash=bcrypt.generate_password_hash("placeholder").decode(),
        )
        db.session.add(user)

    db.session.commit()


