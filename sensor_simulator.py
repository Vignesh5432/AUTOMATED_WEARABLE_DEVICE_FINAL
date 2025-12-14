"""
Virtual sensor simulator for the AI-Based Virtual Wearable Safety System.
Generates realistic per-second readings with optional CSV playback.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

import pandas as pd


def _bounded(value: float, low: float, high: float) -> float:
    """Clamp value into [low, high]."""
    return max(low, min(high, value))


@dataclass
class VirtualSensorSimulator:
    worker_id: str
    dataset: Optional[pd.DataFrame] = None
    dataset_index: int = 0
    last_timestamp: float = field(default_factory=time.time)

    def load_csv_dataset(self, csv_path: Path) -> None:
        """Load dataset from CSV. Expected columns: heart_rate, spo2, temperature, gas, fatigue."""
        df = pd.read_csv(csv_path)
        expected = {"heart_rate", "spo2", "temperature", "gas", "fatigue"}
        missing = expected - set(df.columns)
        if missing:
            raise ValueError(f"Dataset missing columns: {missing}")
        self.dataset = df.reset_index(drop=True)
        self.dataset_index = 0

    def set_dataset(self, df: pd.DataFrame) -> None:
        """Attach an in-memory dataset (e.g., from Streamlit upload)."""
        self.dataset = df.reset_index(drop=True)
        self.dataset_index = 0

    def _sample_from_dataset(self) -> Dict:
        """Return the next row from dataset, cycling when reaching the end."""
        assert self.dataset is not None
        row = self.dataset.iloc[self.dataset_index]
        self.dataset_index = (self.dataset_index + 1) % len(self.dataset)
        return {
            "heart_rate": float(row["heart_rate"]),
            "spo2": float(row["spo2"]),
            "temperature": float(row["temperature"]),
            "gas": float(row["gas"]),
            "fatigue": int(row["fatigue"]),
        }

    def _generate_random_reading(self) -> Dict:
        """
        Generate realistic random values.
        Includes a small probability of abnormal values for demo purposes.
        """
        scenario = random.random()
        if scenario < 0.65:
            # Normal band
            hr = random.gauss(82, 8)
            spo2 = random.gauss(97, 1.5)
            temp = random.gauss(36.9, 0.3)
            gas = abs(random.gauss(20, 10))
        elif scenario < 0.9:
            # Mild abnormal / warning
            hr = random.gauss(110, 10)
            spo2 = random.gauss(92, 2)
            temp = random.gauss(37.8, 0.5)
            gas = abs(random.gauss(90, 25))
        else:
            # Critical abnormal
            hr = random.gauss(135, 12)
            spo2 = random.gauss(86, 3)
            temp = random.gauss(39.5, 0.5)
            gas = abs(random.gauss(190, 25))

        fatigue_prob = random.random()
        if fatigue_prob < 0.7:
            fatigue = 0
        elif fatigue_prob < 0.9:
            fatigue = 1
        else:
            fatigue = 2

        return {
            "heart_rate": _bounded(hr, 50, 180),
            "spo2": _bounded(spo2, 70, 100),
            "temperature": _bounded(temp, 35.0, 41.0),
            "gas": _bounded(gas, 0, 400),
            "fatigue": fatigue,
        }

    def get_reading(self) -> Dict:
        """
        Get the next sensor reading (dataset-driven if present else random).
        A timestamp is attached for downstream logging.
        """
        if self.dataset is not None and len(self.dataset) > 0:
            values = self._sample_from_dataset()
        else:
            values = self._generate_random_reading()

        self.last_timestamp = time.time()
        values["timestamp"] = self.last_timestamp
        values["worker_id"] = self.worker_id
        return values


