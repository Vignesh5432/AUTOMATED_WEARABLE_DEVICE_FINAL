"""Routes serving the HTML pages."""

from __future__ import annotations

from flask import Blueprint, render_template

ui_bp = Blueprint("ui", __name__)


@ui_bp.route("/")
def home():
    return render_template("worker.html", title="Worker Console")


@ui_bp.route("/admin")
def admin():
    return render_template("admin.html", title="Admin Dashboard")


