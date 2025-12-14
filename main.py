"""
CLI entry-point for quick simulation without the Streamlit UI.
"""

from __future__ import annotations

import time

from data_logger import DataLogger
from decision_engine import DecisionEngine
from sensor_simulator import VirtualSensorSimulator


def run_cli(worker_id: str = "Worker-CLI", iterations: int = 20, interval: float = 1.0) -> None:
    simulator = VirtualSensorSimulator(worker_id)
    decision = DecisionEngine()
    logger = DataLogger()

    for _ in range(iterations):
        reading = simulator.get_reading()
        evaluation = decision.evaluate(reading)
        reading["overall"] = evaluation.overall
        logger.log_sensor_data(reading)
        print(
            f"{reading['worker_id']} | HR {reading['heart_rate']:.0f} | "
            f"SpO2 {reading['spo2']:.1f} | Temp {reading['temperature']:.1f} | "
            f"Gas {reading['gas']:.0f} | Fatigue {reading['fatigue']} | Status {evaluation.overall.upper()}"
        )
        time.sleep(interval)


if __name__ == "__main__":
    run_cli()


