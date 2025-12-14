from backend.decision_engine import DecisionEngine


def test_safe_reading():
    engine = DecisionEngine()
    detail = engine.evaluate({"heart_rate": 80, "spo2": 98, "temperature": 36.8, "gas": 20, "fatigue": 0, "zone": "NORMAL"})
    assert detail.status == "SAFE"
    assert detail.final_risk_score <= 40


def test_gas_low_o2_emergency():
    engine = DecisionEngine()
    detail = engine.evaluate({"heart_rate": 110, "spo2": 88, "temperature": 37.2, "gas": 900, "fatigue": 0, "zone": "NORMAL"})
    assert detail.status == "EMERGENCY"
    assert detail.fusion_reason in ("Gas + Low O2", "Parameter >= 95")


def test_fatigue_hr_emergency():
    engine = DecisionEngine()
    detail = engine.evaluate({"heart_rate": 150, "spo2": 95, "temperature": 37.5, "gas": 100, "fatigue": 2, "zone": "NORMAL"})
    assert detail.status == "EMERGENCY"
    assert detail.final_risk_score >= 90


