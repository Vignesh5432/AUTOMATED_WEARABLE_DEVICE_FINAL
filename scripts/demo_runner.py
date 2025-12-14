"""
Demo runner that replays predefined scenarios into the backend via HTTP.
Assumes server running on localhost:5000.
"""
from __future__ import annotations

import time
import requests
import pandas as pd
from pathlib import Path

SERVER = "http://localhost:5000"


def login_worker():
    r = requests.post(f"{SERVER}/login/worker", json={"worker_id": "W-001", "pin": "1234"})
    r.raise_for_status()
    return r.cookies


def send_csv(path: Path, cookies):
    df = pd.read_csv(path)
    start = time.time()
    for _, row in df.iterrows():
        payload = {
            "heart_rate": int(row.heart_rate),
            "spo2": int(row.spo2),
            "temperature": float(row.temperature),
            "gas": int(row.gas),
            "fatigue": int(row.fatigue),
        }
        requests.post(f"{SERVER}/worker/reading", json=payload, cookies=cookies)
        time.sleep(1)
    print(f"Scenario {path.name} done in {time.time() - start:.1f}s")


def main():
    cookies = login_worker()
    for scenario in [
        "scenario_normal.csv",
        "scenario_warning_spo2.csv",
        "scenario_gas_spike.csv",
        "scenario_fatigue_collapse.csv",
    ]:
        send_csv(Path("demo_data") / scenario, cookies)


if __name__ == "__main__":
    main()


