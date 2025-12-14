"""Authentication routes for admin and worker login."""

from __future__ import annotations

from flask import Blueprint, jsonify, request, session
from flask_bcrypt import check_password_hash, generate_password_hash

from backend.db import bcrypt, db
from backend.models import User, Worker

auth_bp = Blueprint("auth", __name__)


def _login_user(user: User):
    session["user_id"] = user.id
    session["role"] = user.role
    session["worker_id"] = user.worker_id


@auth_bp.route("/login/admin", methods=["POST"])
def login_admin():
    data = request.get_json(force=True)
    username = data.get("username")
    password = data.get("password")
    user = User.query.filter_by(username=username, role="admin").first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid credentials"}), 401
    _login_user(user)
    return jsonify({"message": "ok", "role": "admin"})


@auth_bp.route("/login/worker", methods=["POST"])
def login_worker():
    data = request.get_json(force=True)
    worker_id = data.get("worker_id")
    pin = data.get("pin")
    user = User.query.filter_by(worker_id=worker_id, role="worker").first()
    if not user or user.pin != pin:
        return jsonify({"error": "Invalid credentials"}), 401
    _login_user(user)
    return jsonify({"message": "ok", "role": "worker", "worker_id": worker_id})


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "logged out"})


def ensure_admin():
    if session.get("role") != "admin":
        return False
    return True


def ensure_worker():
    if session.get("role") == "worker" and session.get("worker_id"):
        return True
    return False


