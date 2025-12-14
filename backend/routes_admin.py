"""Admin-facing endpoints for monitoring, acknowledgements, actions, and reports."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
from flask import Blueprint, jsonify, request, session

import config
from backend.alerts import create_or_update_alert, escalate_overdue_emergencies
from backend.auth import ensure_admin
from backend.db import db
from backend.models import Alert, Message, Reading, Worker

admin_bp = Blueprint("admin", __name__)


def _require_admin():
    if not ensure_admin():
        return jsonify({"error": "unauthorized"}), 401
    return None


def _check_unconscious():
    now = dt.datetime.utcnow()
    workers = Worker.query.all()
    for w in workers:
        delta = (now - (w.last_seen or now)).total_seconds()
        if delta > config.INACTIVITY_TIMEOUT:
            last_reading = (
                Reading.query.filter_by(worker_id=w.worker_id)
                .order_by(Reading.timestamp.desc())
                .first()
            )
            if last_reading is None or last_reading.status in {"SAFE", "WARNING"}:
                create_or_update_alert(
                    w.worker_id, "UNCONSCIOUS", "EMERGENCY", "No recent activity — possible unconsciousness"
                )


@admin_bp.route("/workers", methods=["GET"])
def workers():
    err = _require_admin()
    if err:
        return err
    _check_unconscious()
    escalate_overdue_emergencies()
    workers = Worker.query.all()
    payload = []
    for w in workers:
        last_reading = (
            Reading.query.filter_by(worker_id=w.worker_id)
            .order_by(Reading.timestamp.desc())
            .first()
        )
        payload.append(
            {
                "worker_id": w.worker_id,
                "name": w.name,
                "zone": w.zone,
                "last_seen": w.last_seen.isoformat() if w.last_seen else None,
                "status": last_reading.status if last_reading else "UNKNOWN",
                "risk_score": last_reading.risk_score if last_reading else None,
                "heart_rate": last_reading.heart_rate if last_reading else None,
                "spo2": last_reading.spo2 if last_reading else None,
                "temperature": last_reading.temperature if last_reading else None,
                "gas": last_reading.gas if last_reading else None,
                "fatigue": last_reading.fatigue if last_reading else None,
                "last_reading_ts": last_reading.timestamp.isoformat() if last_reading else None,
            }
        )
    return jsonify(payload)


@admin_bp.route("/latest/<worker_id>", methods=["GET"])
def latest(worker_id):
    err = _require_admin()
    if err:
        return err
    reading = (
        Reading.query.filter_by(worker_id=worker_id)
        .order_by(Reading.timestamp.desc())
        .first()
    )
    if not reading:
        return jsonify({"error": "no data"}), 404
    return jsonify(
        {
            "timestamp": reading.timestamp.isoformat(),
            "heart_rate": reading.heart_rate,
            "spo2": reading.spo2,
            "temperature": reading.temperature,
            "gas": reading.gas,
            "fatigue": reading.fatigue,
            "risk_score": reading.risk_score,
            "status": reading.status,
        }
    )


@admin_bp.route("/alerts", methods=["GET"])
def alerts():
    err = _require_admin()
    if err:
        return err
    active = Alert.query.filter_by(resolved=False).order_by(Alert.timestamp.desc()).all()
    return jsonify(
        [
            {
                "id": a.id,
                "worker_id": a.worker_id,
                "timestamp": a.timestamp.isoformat(),
                "alert_type": a.alert_type,
                "priority": a.priority,
                "reason": a.reason,
                "acknowledged_by": a.acknowledged_by,
                "resolved": a.resolved,
                "count": a.count,
                "escalation_flag": a.escalation_flag,
            }
            for a in active
        ]
    )


@admin_bp.route("/worker/<worker_id>/history", methods=["GET"])
def worker_history(worker_id):
    err = _require_admin()
    if err:
        return err
    minutes = int(request.args.get("minutes", 6))
    since = dt.datetime.utcnow() - dt.timedelta(minutes=minutes)
    readings = (
        Reading.query.filter(Reading.worker_id == worker_id, Reading.timestamp >= since)
        .order_by(Reading.timestamp.asc())
        .all()
    )
    return jsonify(
        [
            {
                "timestamp": r.timestamp.isoformat(),
                "heart_rate": r.heart_rate,
                "spo2": r.spo2,
                "temperature": r.temperature,
                "gas": r.gas,
                "fatigue": r.fatigue,
                "risk_score": r.risk_score,
                "status": r.status,
            }
            for r in readings
        ]
    )


@admin_bp.route("/message", methods=["POST"])
def send_message():
    err = _require_admin()
    if err:
        return err
    payload = request.get_json(force=True)
    worker_id = payload.get("worker_id")
    if not worker_id:
        return jsonify({"error": "worker_id required"}), 400
    if not Worker.query.filter_by(worker_id=worker_id).first():
        return jsonify({"error": "worker not found"}), 404
    message_text = payload.get("message")
    command = None
    if payload.get("action") == "STOP WORK":
        command = "STOP WORK"
    msg = Message(from_role="ADMIN", to_worker_id=worker_id, message=message_text, command=command)
    db.session.add(msg)
    if command:
        create_or_update_alert(worker_id, "ADMIN", "EMERGENCY", "Admin issued STOP WORK")
    db.session.commit()
    return jsonify({"message": "sent"})


@admin_bp.route("/ack_alert", methods=["POST"])
def ack_alert():
    err = _require_admin()
    if err:
        return err
    payload = request.get_json(force=True)
    alert_id = payload.get("alert_id")
    admin_user = payload.get("admin_user", session.get("user_id"))
    alert = Alert.query.get(alert_id)
    if not alert:
        return jsonify({"error": "alert not found"}), 404
    alert.acknowledged_by = admin_user
    alert.acknowledged_at = dt.datetime.utcnow()
    db.session.commit()
    return jsonify({"message": "acknowledged"})


@admin_bp.route("/resolve_alert", methods=["POST"])
def resolve_alert():
    err = _require_admin()
    if err:
        return err
    payload = request.get_json(force=True)
    alert_id = payload.get("alert_id")
    alert = Alert.query.get(alert_id)
    if not alert:
        return jsonify({"error": "alert not found"}), 404
    alert.resolved = True
    db.session.commit()
    return jsonify({"message": "resolved"})


@admin_bp.route("/action", methods=["POST"])
def admin_action():
    err = _require_admin()
    if err:
        return err
    payload = request.get_json(force=True)
    worker_id = payload.get("worker_id")
    action = payload.get("action")
    if action not in {"ALLOW", "RESTRICT", "STOP"}:
        return jsonify({"error": "invalid action"}), 400
    reason = f"Admin action: {action}"
    priority = "EMERGENCY" if action == "STOP" else "WARNING"
    create_or_update_alert(worker_id, "ADMIN", priority, reason)
    msg = Message(from_role="ADMIN", to_worker_id=worker_id, message=reason, command="STOP WORK" if action == "STOP" else None)
    db.session.add(msg)
    db.session.commit()
    return jsonify({"message": "action applied"})


@admin_bp.route("/report/daily", methods=["GET"])
def daily_report():
    err = _require_admin()
    if err:
        return err
    date_str = request.args.get("date")
    date = dt.datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else dt.date.today()
    start = dt.datetime.combine(date, dt.time.min)
    end = dt.datetime.combine(date, dt.time.max)

    readings = Reading.query.filter(Reading.timestamp >= start, Reading.timestamp <= end).all()
    alerts = Alert.query.filter(Alert.timestamp >= start, Alert.timestamp <= end).all()

    if not readings:
        return jsonify({"error": "no data"}), 404

    df = pd.DataFrame(
        [
            {
                "worker_id": r.worker_id,
                "timestamp": r.timestamp,
                "risk_score": r.risk_score,
                "status": r.status,
                "heart_rate": r.heart_rate,
                "spo2": r.spo2,
                "temperature": r.temperature,
                "gas": r.gas,
            }
            for r in readings
        ]
    )
    summary_rows = []
    for worker_id, group in df.groupby("worker_id"):
        total = len(group)
        safe = (group["status"] == "SAFE").sum()
        warning = (group["status"] == "WARNING").sum()
        emergency = (group["status"] == "EMERGENCY").sum()
        summary_rows.append(
            {
                "worker_id": worker_id,
                "date": date,
                "total_readings": total,
                "total_alerts": len([a for a in alerts if a.worker_id == worker_id]),
                "avg_hr": round(group["heart_rate"].mean(), 2),
                "avg_spo2": round(group["spo2"].mean(), 2),
                "avg_temp": round(group["temperature"].mean(), 2),
                "avg_gas": round(group["gas"].mean(), 2),
                "%safe": round(safe / total * 100, 2),
                "%warning": round(warning / total * 100, 2),
                "%emergency": round(emergency / total * 100, 2),
            }
        )
    summary_df = pd.DataFrame(summary_rows)
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    report_path = reports_dir / f"daily_report_{date}.csv"
    summary_df.to_csv(report_path, index=False)

    alerts_path = reports_dir / f"alerts_{date}.csv"
    pd.DataFrame(
        [
            {
                "timestamp": a.timestamp,
                "worker_id": a.worker_id,
                "alert_type": a.alert_type,
                "priority": a.priority,
                "reason": a.reason,
                "acknowledged_by": a.acknowledged_by,
                "resolved": a.resolved,
            }
            for a in alerts
        ]
    ).to_csv(alerts_path, index=False)

    return jsonify({"summary": str(report_path), "alerts": str(alerts_path)})


