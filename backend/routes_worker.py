"""Worker-facing endpoints and polling logic."""

from __future__ import annotations

import datetime as dt

from flask import Blueprint, jsonify, request, session

import config
from backend.alerts import create_or_update_alert
from backend.auth import ensure_worker
from backend.db import db
from backend.decision_engine import DecisionEngine
from backend.models import Message, Reading, Worker
from backend.rate_limit import allow as rate_allow

worker_bp = Blueprint("worker", __name__)
engine = DecisionEngine()


def _require_worker():
    if not ensure_worker():
        return jsonify({"error": "unauthorized"}), 401
    return None


@worker_bp.route("/profile", methods=["GET"])
def profile():
    err = _require_worker()
    if err:
        return err
    worker_id = session.get("worker_id")
    worker = Worker.query.filter_by(worker_id=worker_id).first()
    return jsonify({"worker_id": worker.worker_id, "name": worker.name, "zone": worker.zone})


def _process_reading(payload: dict, worker: Worker):
    required = ["heart_rate", "spo2", "temperature", "gas", "fatigue"]
    if not all(k in payload for k in required):
        return jsonify({"error": "missing fields"}), 400

    if not rate_allow(worker.worker_id):
        return jsonify({"error": "rate limit"}), 429

    reading = {
        "worker_id": worker.worker_id,
        "heart_rate": payload["heart_rate"],
        "spo2": payload["spo2"],
        "temperature": payload["temperature"],
        "gas": payload["gas"],
        "fatigue": payload["fatigue"],
        "zone": worker.zone,
    }

    detail = engine.evaluate(reading)
    rec = Reading(
        worker_id=worker.worker_id,
        timestamp=dt.datetime.utcnow(),
        heart_rate=reading["heart_rate"],
        spo2=reading["spo2"],
        temperature=reading["temperature"],
        gas=reading["gas"],
        fatigue=reading["fatigue"],
        risk_score=detail.final_risk_score,
        status=detail.status,
    )
    db.session.add(rec)
    worker.last_seen = dt.datetime.utcnow()

    play_sound = False
    banner = False

    if detail.status in ("WARNING", "EMERGENCY"):
        priority = "EMERGENCY" if detail.status == "EMERGENCY" else "WARNING"
        alert, created = create_or_update_alert(worker.worker_id, "AI", priority, detail.fusion_reason)
        play_sound = detail.status == "EMERGENCY" or created
        banner = True

    db.session.commit()

    response = {
        "status": detail.status,
        "risk_score": detail.final_risk_score,
        "detail": {
            "parameter_risks": detail.parameter_risks,
            "reasons": detail.reasons,
            "fusion_reason": detail.fusion_reason,
        },
        "play_sound": play_sound,
        "banner": banner,
    }
    return jsonify(response)


@worker_bp.route("/reading", methods=["POST"])
def submit_reading():
    err = _require_worker()
    if err:
        return err
    worker = Worker.query.filter_by(worker_id=session["worker_id"]).first()
    payload = request.get_json(force=True)
    return _process_reading(payload, worker)


@worker_bp.route("/hazard", methods=["POST"])
def hazard():
    err = _require_worker()
    if err:
        return err
    worker_id = session["worker_id"]
    payload = request.get_json(force=True)
    htype = payload.get("type")
    if htype not in {"GAS_LEAK", "FIRE", "OXYGEN_DROP", "HEAT_BURST"}:
        return jsonify({"error": "invalid hazard type"}), 400
    create_or_update_alert(worker_id, "HAZARD", "EMERGENCY", f"Hazard reported: {htype}")
    return jsonify({"message": "hazard reported", "play_sound": True, "banner": True})


@worker_bp.route("/emergency", methods=["POST"])
def emergency():
    err = _require_worker()
    if err:
        return err
    worker_id = session["worker_id"]
    create_or_update_alert(worker_id, "MANUAL", "EMERGENCY", "Manual emergency button pressed")
    return jsonify({"message": "emergency sent", "play_sound": True, "banner": True})


@worker_bp.route("/poll", methods=["POST"])
def poll():
    err = _require_worker()
    if err:
        return err
    worker_id = session["worker_id"]
    worker = Worker.query.filter_by(worker_id=worker_id).first()
    worker.last_seen = dt.datetime.utcnow()
    db.session.commit()

    since = dt.datetime.utcnow() - dt.timedelta(minutes=6)
    history = (
        Reading.query.filter(Reading.worker_id == worker_id, Reading.timestamp >= since)
        .order_by(Reading.timestamp.asc())
        .all()
    )
    history_payload = [
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
        for r in history
    ]

    messages = Message.query.filter_by(to_worker_id=worker_id, delivered=False).all()
    msg_payload = [
        {
            "id": m.id,
            "from_role": m.from_role,
            "message": m.message,
            "command": m.command,
            "timestamp": m.timestamp.isoformat(),
        }
        for m in messages
    ]
    for m in messages:
        m.delivered = True
    db.session.commit()

    last_reading = (
        Reading.query.filter_by(worker_id=worker_id).order_by(Reading.timestamp.desc()).first()
    )
    latest_status = last_reading.status if last_reading else "SAFE"

    alerts_flag = latest_status in {"WARNING", "EMERGENCY"}

    return jsonify(
        {
            "status": latest_status,
            "history": history_payload,
            "messages": msg_payload,
            "play_sound": alerts_flag,
            "banner": alerts_flag,
        }
    )


@worker_bp.route("/ack_message", methods=["POST"])
def ack_message():
    err = _require_worker()
    if err:
        return err
    payload = request.get_json(force=True)
    mid = payload.get("id")
    msg = Message.query.get(mid)
    if not msg:
        return jsonify({"error": "not found"}), 404
    msg.delivered = True
    db.session.commit()
    return jsonify({"message": "acknowledged"})


