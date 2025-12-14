"""
Data logging utilities for sensor readings, alerts, and daily reports.
"""

from __future__ import annotations

import csv
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import pandas as pd


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class DataLogger:
    sensor_log_path: Path = Path("logs/sensor_data.csv")
    alert_log_path: Path = Path("logs/alerts.csv")
    report_path: Path = Path("logs/daily_report.csv")

    def __post_init__(self):
        _ensure_parent(self.sensor_log_path)
        _ensure_parent(self.alert_log_path)
        _ensure_parent(self.report_path)
        self._init_file(self.sensor_log_path, ["timestamp", "worker_id", "heart_rate", "spo2", "temperature", "gas", "fatigue"])
        self._init_file(self.alert_log_path, ["timestamp", "worker_id", "overall_status", "reason"])

    def _init_file(self, path: Path, header: list) -> None:
        if not path.exists():
            with path.open("w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(header)

    def log_sensor_data(self, reading: Dict) -> None:
        row = [
            dt.datetime.fromtimestamp(reading["timestamp"]).isoformat(),
            reading["worker_id"],
            reading["heart_rate"],
            reading["spo2"],
            reading["temperature"],
            reading["gas"],
            reading["fatigue"],
        ]
        with self.sensor_log_path.open("a", newline="") as f:
            csv.writer(f).writerow(row)

    def log_alert(self, reading: Dict, reason: str) -> None:
        row = [
            dt.datetime.fromtimestamp(reading["timestamp"]).isoformat(),
            reading["worker_id"],
            reading.get("overall", "unknown"),
            reason,
        ]
        with self.alert_log_path.open("a", newline="") as f:
            csv.writer(f).writerow(row)

    def generate_daily_report(self) -> Path:
        """Aggregate the latest day's data into a report CSV."""
        if not self.sensor_log_path.exists():
            return self.report_path

        df = pd.read_csv(self.sensor_log_path)
        if df.empty:
            return self.report_path

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        today = pd.Timestamp.now().normalize()
        df_today = df[df["timestamp"] >= today]

        summary = {
            "date": today.date(),
            "total_readings": len(df_today),
            "mean_heart_rate": round(df_today["heart_rate"].mean(), 2),
            "min_spo2": df_today["spo2"].min(),
            "max_temperature": df_today["temperature"].max(),
            "max_gas": df_today["gas"].max(),
            "fatigue_events": int((df_today["fatigue"] >= 1).sum()),
        }

        self._init_file(self.report_path, list(summary.keys()))
        with self.report_path.open("a", newline="") as f:
            csv.writer(f).writerow(summary.values())
        return self.report_path


