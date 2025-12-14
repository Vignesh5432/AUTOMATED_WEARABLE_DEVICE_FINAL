"""Alert management: creation, cooldown handling, escalation checks."""

from __future__ import annotations

import datetime as dt
from typing import Optional, Tuple

import config
from backend.db import db
from backend.models import Alert


def _within_cooldown(existing: Alert) -> bool:
    return (dt.datetime.utcnow() - existing.timestamp).total_seconds() <= config.ALERT_COOLDOWN


def create_or_update_alert(worker_id: str, alert_type: str, priority: str, reason: str) -> Tuple[Alert, bool]:
    """
    Create a new alert or update timestamp/count if within cooldown.
    Returns (alert, created_flag).
    """
    existing = (
        Alert.query.filter_by(worker_id=worker_id, alert_type=alert_type, resolved=False)
        .order_by(Alert.timestamp.desc())
        .first()
    )
    if existing and _within_cooldown(existing):
        existing.timestamp = dt.datetime.utcnow()
        existing.count = (existing.count or 1) + 1
        db.session.commit()
        return existing, False

    alert = Alert(
        worker_id=worker_id,
        alert_type=alert_type,
        priority=priority,
        reason=reason,
        timestamp=dt.datetime.utcnow(),
    )
    db.session.add(alert)
    db.session.commit()
    return alert, True


def escalate_overdue_emergencies():
    """
    If an EMERGENCY alert is unacknowledged beyond threshold, mark escalation_flag.
    """
    now = dt.datetime.utcnow()
    overdue = Alert.query.filter(
        Alert.priority == "EMERGENCY",
        Alert.acknowledged_at.is_(None),
        Alert.escalation_flag.is_(False),
        Alert.resolved.is_(False),
    )
    for alert in overdue:
        if (now - alert.timestamp).total_seconds() > config.ESCALATE_AFTER_SECONDS:
            alert.escalation_flag = True
    db.session.commit()


