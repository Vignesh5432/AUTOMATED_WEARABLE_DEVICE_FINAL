"""
Decision engine implementing rule-based health, gas, fatigue, and fusion logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class ParameterStatus:
    level: str  # "normal" | "warning" | "critical"
    reason: str


@dataclass
class EvaluationResult:
    overall: str  # "safe" | "warning" | "emergency"
    parameter_status: Dict[str, ParameterStatus]
    triggers: List[str]


class DecisionEngine:
    """Encapsulates thresholds and multi-parameter fusion logic."""

    def __init__(self):
        self.spo2_low = 90
        self.hr_high = 120
        self.temp_high = 38.5
        self.gas_warning = 50
        self.gas_critical = 150

    def _health_status(self, hr: float, spo2: float, temp: float) -> Tuple[List[str], Dict[str, ParameterStatus]]:
        triggers = []
        status: Dict[str, ParameterStatus] = {}

        if spo2 < self.spo2_low:
            status["spo2"] = ParameterStatus("critical", "Respiratory Risk: SpO2 below 90%")
            triggers.append("respiratory_risk")
        else:
            status["spo2"] = ParameterStatus("normal", "SpO2 within safe range")

        if hr > self.hr_high:
            status["heart_rate"] = ParameterStatus("critical", "Cardiac Stress: Heart rate above 120 bpm")
            triggers.append("cardiac_stress")
        elif hr > 100:
            status["heart_rate"] = ParameterStatus("warning", "Elevated heart rate >100 bpm")
        else:
            status["heart_rate"] = ParameterStatus("normal", "Heart rate normal")

        if temp > self.temp_high:
            status["temperature"] = ParameterStatus("critical", "Heat/Fever Risk: Temperature > 38.5°C")
            triggers.append("fever_risk")
        elif temp > 37.8:
            status["temperature"] = ParameterStatus("warning", "Temperature slightly elevated")
        else:
            status["temperature"] = ParameterStatus("normal", "Temperature normal")

        return triggers, status

    def _gas_status(self, gas: float) -> Tuple[List[str], ParameterStatus]:
        triggers: List[str] = []
        if gas > self.gas_critical:
            triggers.append("gas_critical")
            return triggers, ParameterStatus("critical", "Gas Critical: >150 PPM")
        if gas > self.gas_warning:
            triggers.append("gas_warning")
            return triggers, ParameterStatus("warning", "Gas Warning: 50-150 PPM")
        return triggers, ParameterStatus("normal", "Gas Safe: <50 PPM")

    def _fatigue_status(self, fatigue: int) -> Tuple[List[str], ParameterStatus]:
        triggers: List[str] = []
        if fatigue >= 2:
            triggers.append("fatigue_critical")
            return triggers, ParameterStatus("critical", "Fatigue Critical: Drowsiness detected")
        if fatigue == 1:
            triggers.append("fatigue_warning")
            return triggers, ParameterStatus("warning", "Fatigue Warning: Reduced alertness")
        return triggers, ParameterStatus("normal", "Fatigue Normal")

    def _fusion_logic(self, parameter_status: Dict[str, ParameterStatus], triggers: List[str]) -> str:
        """Multi-parameter fusion following the provided rules."""
        gas_status = parameter_status["gas"].level
        spo2_low = "respiratory_risk" in triggers
        hr_high = parameter_status["heart_rate"].level == "critical"
        fatigue_critical = "fatigue_critical" in triggers

        # Example fusion rules
        if gas_status == "critical" and spo2_low:
            return "emergency"
        if fatigue_critical and hr_high:
            return "emergency"
        if any(p.level == "critical" for p in parameter_status.values()):
            return "warning"
        if any(p.level == "warning" for p in parameter_status.values()):
            return "warning"
        return "safe"

    def evaluate(self, reading: Dict) -> EvaluationResult:
        """Evaluate a single reading and return detailed statuses."""
        triggers: List[str] = []
        health_triggers, health_status = self._health_status(
            hr=reading["heart_rate"], spo2=reading["spo2"], temp=reading["temperature"]
        )
        triggers.extend(health_triggers)

        gas_triggers, gas_status = self._gas_status(reading["gas"])
        triggers.extend(gas_triggers)

        fatigue_triggers, fatigue_status = self._fatigue_status(reading["fatigue"])
        triggers.extend(fatigue_triggers)

        parameter_status = {**health_status, "gas": gas_status, "fatigue": fatigue_status}
        overall = self._fusion_logic(parameter_status, triggers)
        return EvaluationResult(overall=overall, parameter_status=parameter_status, triggers=triggers)


