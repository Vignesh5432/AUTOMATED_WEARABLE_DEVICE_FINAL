"""SQLAlchemy models for users, workers, readings, alerts, messages."""

from __future__ import annotations

import datetime as dt

from backend.db import db


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    role = db.Column(db.String, nullable=False)  # admin | worker
    worker_id = db.Column(db.String, nullable=True)
    pin = db.Column(db.String, nullable=True)


class Worker(db.Model):
    __tablename__ = "workers"
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.String, unique=True, nullable=False)
    name = db.Column(db.String, nullable=False)
    zone = db.Column(db.String, nullable=False, default="NORMAL")
    last_seen = db.Column(db.DateTime, default=dt.datetime.utcnow)


class Reading(db.Model):
    __tablename__ = "readings"
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.String, nullable=False)
    timestamp = db.Column(db.DateTime, default=dt.datetime.utcnow)
    heart_rate = db.Column(db.Integer)
    spo2 = db.Column(db.Integer)
    temperature = db.Column(db.Float)
    gas = db.Column(db.Integer)
    fatigue = db.Column(db.Integer)
    risk_score = db.Column(db.Integer)
    status = db.Column(db.String)


class Alert(db.Model):
    __tablename__ = "alerts"
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.String, nullable=False)
    timestamp = db.Column(db.DateTime, default=dt.datetime.utcnow)
    alert_type = db.Column(db.String)  # AI | MANUAL | UNCONSCIOUS | HAZARD | ADMIN
    priority = db.Column(db.String)  # INFO | WARNING | EMERGENCY
    reason = db.Column(db.String)
    acknowledged_by = db.Column(db.String, nullable=True)
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    resolved = db.Column(db.Boolean, default=False)
    count = db.Column(db.Integer, default=1)
    escalation_flag = db.Column(db.Boolean, default=False)


class Message(db.Model):
    __tablename__ = "messages"
    id = db.Column(db.Integer, primary_key=True)
    from_role = db.Column(db.String)  # ADMIN | WORKER | SYSTEM
    to_worker_id = db.Column(db.String)
    timestamp = db.Column(db.DateTime, default=dt.datetime.utcnow)
    message = db.Column(db.String)
    delivered = db.Column(db.Boolean, default=False)
    command = db.Column(db.String, nullable=True)  # optional command e.g., STOP WORK


