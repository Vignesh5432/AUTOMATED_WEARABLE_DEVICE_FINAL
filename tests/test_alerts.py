import datetime as dt

from backend.alerts import create_or_update_alert
from backend.db import db
from backend.models import Alert
from backend import create_app


def setup_module(module):
    app = create_app()
    app.testing = True
    module.ctx = app.app_context()
    module.ctx.push()
    db.drop_all()
    db.create_all()


def teardown_module(module):
    db.session.remove()
    db.drop_all()
    module.ctx.pop()


def test_alert_cooldown():
    alert, created = create_or_update_alert("W-001", "AI", "WARNING", "test")
    assert created
    alert2, created2 = create_or_update_alert("W-001", "AI", "WARNING", "test")
    assert not created2
    assert alert2.count >= 2


