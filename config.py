"""
Global configuration for the Industrial Worker Safety Monitoring Web App.
Adjust ZONE_SENSITIVITY here if needed.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "safety.db")
SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_PATH}"
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = os.environ.get("SAFETY_APP_SECRET", "dev-secret-change-me")
SESSION_COOKIE_NAME = "safety_session"

# Zone sensitivity factors
ZONE_SENSITIVITY = {
    "NORMAL": 1.0,
    "CHEMICAL": 0.7,
    "MINING": 0.8,
    "FIRE-RESCUE": 0.85,
}

# Inactivity timeout in seconds for unconscious detection
INACTIVITY_TIMEOUT = 45

# Alert cooldown window in seconds per worker per alert type
ALERT_COOLDOWN = 30

# Escalation threshold for unacknowledged emergency alerts
ESCALATE_AFTER_SECONDS = 60

# Rate limiting: max readings per worker per second
RATE_LIMIT_READINGS_PER_SEC = 2

