"""
Deterministic fusion decision engine implementing specified risk logic.
Designed to be swappable with ML later without changing API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import config


@dataclass
class DecisionDetail:
    parameter_risks: Dict[str, int]
    reasons: Dict[str, str]
    fusion_reason: str
    final_risk_score: int
    status: str


class DecisionEngine:
    def __init__(self):
        self.zone_sensitivity = config.ZONE_SENSITIVITY

    @staticmethod
    def _clamp(val, low, high):
        return max(low, min(high, val))

    def _zone_factor(self, zone: str) -> float:
        return self.zone_sensitivity.get(zone.upper(), 1.0)

    def evaluate(self, reading: Dict) -> DecisionDetail:
        zone = reading.get("zone", "NORMAL") or "NORMAL"
        factor = self._zone_factor(zone)

        hr = self._clamp(int(reading["heart_rate"]), 30, 220)
        spo2 = self._clamp(int(reading["spo2"]), 50, 100)
        temp = self._clamp(float(reading["temperature"]), 28, 45)
        gas = self._clamp(int(reading["gas"]), 0, 5000)
        fatigue_in = reading["fatigue"]
        fatigue = {"low": 0, "medium": 1, "high": 2}.get(str(fatigue_in).lower(), int(fatigue_in))

        reasons = {}

        # HR risk
        if hr < 40:
            hr_risk = 80
        elif hr < 50:
            hr_risk = 60
        elif hr <= 100:
            hr_risk = 10
        elif hr <= 120:
            hr_risk = 40
        elif hr <= 140:
            hr_risk = 60
        elif hr <= 180:
            hr_risk = 85
        else:
            hr_risk = 95
        reasons["heart_rate"] = f"HR {hr} -> risk {hr_risk}"

        # SpO2 risk
        if spo2 >= 95:
            spo2_risk = 5
        elif spo2 >= 92:
            spo2_risk = 20
        elif spo2 >= 90:
            spo2_risk = 45
        elif spo2 >= 85:
            spo2_risk = 70
        else:
            spo2_risk = 95
        spo2_risk = min(95, int(spo2_risk / factor))
        reasons["spo2"] = f"SpO2 {spo2}% -> risk {spo2_risk}"

        # Temperature risk
        if temp < 35:
            temp_risk = 30
        elif temp <= 38:
            temp_risk = 10
        elif temp <= 39.5:
            temp_risk = 45
        elif temp <= 41:
            temp_risk = 80
        else:
            temp_risk = 95
        reasons["temperature"] = f"Temp {temp}C -> risk {temp_risk}"

        # Gas risk with zone sensitivity
        if gas <= 50:
            gas_risk = 5
        elif gas <= 200:
            gas_risk = 25
        elif gas <= 400:
            gas_risk = 60
        elif gas <= 1000:
            gas_risk = 85
        else:
            gas_risk = 95
        gas_risk = min(95, int(gas_risk / factor if factor else gas_risk))
        reasons["gas"] = f"Gas {gas}ppm zone {zone} -> risk {gas_risk}"

        # Fatigue risk
        fatigue_map = {0: 5, 1: 35, 2: 70}
        fatigue_risk = fatigue_map.get(fatigue, 70)
        reasons["fatigue"] = f"Fatigue {fatigue} -> risk {fatigue_risk}"

        parameter_risks = {
            "heart_rate": hr_risk,
            "spo2": spo2_risk,
            "temperature": temp_risk,
            "gas": gas_risk,
            "fatigue": fatigue_risk,
        }

        health_component = round((hr_risk * 0.4 + spo2_risk * 0.4 + temp_risk * 0.2))
        final_risk = round(health_component * 0.35 + gas_risk * 0.35 + fatigue_risk * 0.30)
        final_risk = self._clamp(final_risk, 0, 100)
        fusion_reason = "Base fusion"

        # Overrides
        def elevate(value, minimum):
            return max(value, minimum)

        high_params = sum(1 for r in parameter_risks.values() if r >= 70)

        if gas_risk >= 85 and spo2_risk >= 45:
            final_risk = elevate(final_risk, 92)
            fusion_reason = "Gas + Low O2"
        if fatigue_risk >= 70 and hr_risk >= 60:
            final_risk = elevate(final_risk, 90)
            fusion_reason = "Critical fatigue + High HR"
        if temp_risk >= 80 and hr_risk >= 60:
            final_risk = elevate(final_risk, 90)
            fusion_reason = "Heat Stress"
        if high_params >= 2:
            final_risk = elevate(final_risk, 88)
            fusion_reason = fusion_reason or "Multiple high risks"
        if any(r >= 95 for r in parameter_risks.values()):
            final_risk = 98
            fusion_reason = "Parameter >= 95"

        if final_risk <= 40:
            status = "SAFE"
        elif final_risk <= 70:
            status = "WARNING"
        else:
            status = "EMERGENCY"

        return DecisionDetail(
            parameter_risks=parameter_risks,
            reasons=reasons,
            fusion_reason=fusion_reason,
            final_risk_score=final_risk,
            status=status,
        )


