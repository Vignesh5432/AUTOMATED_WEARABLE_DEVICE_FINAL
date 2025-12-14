"""
Streamlit dashboard for the Virtual Wearable Safety Monitoring simulation.
"""

from __future__ import annotations

import time
from typing import Dict

import pandas as pd
import streamlit as st

from alert_system import AlertSystem
from data_logger import DataLogger
from decision_engine import DecisionEngine
from sensor_simulator import VirtualSensorSimulator


PAGE_TITLE = "AI-Based Virtual Wearable Safety Monitor"
REFRESH_MS = 1000  # 1 second
MAX_HISTORY = 360  # keep last 6 minutes of data


def init_state():
    if "data_logger" not in st.session_state:
        st.session_state.data_logger = DataLogger()
    if "decision_engine" not in st.session_state:
        st.session_state.decision_engine = DecisionEngine()
    if "alert_system" not in st.session_state:
        st.session_state.alert_system = AlertSystem(st.session_state.data_logger)
    if "simulators" not in st.session_state:
        st.session_state.simulators: Dict[str, VirtualSensorSimulator] = {}
    if "history" not in st.session_state:
        st.session_state.history: Dict[str, pd.DataFrame] = {}
    if "alerts" not in st.session_state:
        st.session_state.alerts = []


def get_simulator(worker_id: str) -> VirtualSensorSimulator:
    sims = st.session_state.simulators
    if worker_id not in sims:
        sims[worker_id] = VirtualSensorSimulator(worker_id=worker_id)
    return sims[worker_id]


def append_history(worker_id: str, reading: Dict) -> pd.DataFrame:
    df = st.session_state.history.get(worker_id)
    row = pd.DataFrame([{
        "timestamp": pd.to_datetime(reading["timestamp"], unit="s"),
        "heart_rate": reading["heart_rate"],
        "spo2": reading["spo2"],
        "temperature": reading["temperature"],
        "gas": reading["gas"],
        "fatigue": reading["fatigue"],
        "overall": reading.get("overall", ""),
    }])
    if df is None or df.empty:
        df = row
    else:
        df = pd.concat([df, row], ignore_index=True)
    if len(df) > MAX_HISTORY:
        df = df.iloc[-MAX_HISTORY:]
    st.session_state.history[worker_id] = df
    return df


def status_badge(status: str) -> str:
    color = {"safe": "#12b981", "warning": "#facc15", "emergency": "#ef4444"}.get(status, "#9ca3af")
    text = status.upper()
    return f"""
    <div style="padding:8px 12px;border-radius:8px;background:{color};color:black;font-weight:700;">
        {text}
    </div>
    """


def render_metrics(reading: Dict):
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Heart Rate (bpm)", f"{reading['heart_rate']:.0f}")
    col2.metric("SpO₂ (%)", f"{reading['spo2']:.1f}")
    col3.metric("Temperature (°C)", f"{reading['temperature']:.1f}")
    col4.metric("Gas (PPM)", f"{reading['gas']:.0f}")
    col5.metric("Fatigue (0=ok)", int(reading["fatigue"]))


def render_charts(history: pd.DataFrame):
    if history is None or history.empty:
        st.info("Waiting for data...")
        return
    st.line_chart(history.set_index("timestamp")[["heart_rate", "spo2", "temperature", "gas"]])
    st.area_chart(history.set_index("timestamp")[["fatigue"]])


def render_alerts():
    if not st.session_state.alerts:
        st.caption("No alerts yet.")
        return
    st.write("Recent Alerts")
    for msg in reversed(st.session_state.alerts[-10:]):
        st.warning(msg, icon="⚠️")


def main():
    st.set_page_config(page_title=PAGE_TITLE, page_icon="🦺", layout="wide")
    init_state()
    st.title(PAGE_TITLE)
    st.caption("Software-only simulation of an industrial wearable safety device.")

    worker_id = st.selectbox("Select Worker", ["Worker-1", "Worker-2", "Worker-3"], index=0)
    simulator = get_simulator(worker_id)

    st.sidebar.header("Data Source")
    uploaded = st.sidebar.file_uploader("Optional: Upload CSV data", type=["csv"])
    if uploaded:
        df = pd.read_csv(uploaded)
        try:
            simulator.set_dataset(df)
            st.sidebar.success("Dataset loaded for this worker.")
        except Exception as exc:  # pragma: no cover - user input guard
            st.sidebar.error(f"Dataset error: {exc}")

    st.sidebar.markdown("Report & Logs")
    if st.sidebar.button("Generate today's report"):
        report_path = st.session_state.data_logger.generate_daily_report()
        st.sidebar.success(f"Report saved to {report_path}")

    auto_refresh = st.sidebar.checkbox("Auto-refresh every second", value=True)

    reading = simulator.get_reading()
    evaluation = st.session_state.decision_engine.evaluate(reading)
    reading["overall"] = evaluation.overall

    st.session_state.data_logger.log_sensor_data(reading)

    st.markdown(status_badge(evaluation.overall), unsafe_allow_html=True)
    render_metrics(reading)

    history = append_history(worker_id, reading)
    render_charts(history)

    if st.session_state.alert_system.should_alert(evaluation.overall):
        message, audio_bytes = st.session_state.alert_system.handle_alert(reading, evaluation.overall.upper())
        st.session_state.alerts.append(message)
        st.toast(message, icon="🚨")
        st.audio(audio_bytes, format="audio/wav")
        flash_color = "#ef4444" if evaluation.overall == "emergency" else "#facc15"
        st.markdown(
            f"<div style='padding:10px;border-radius:6px;background:{flash_color};color:black;font-weight:700;'>"
            f"ALERT: {message}</div>",
            unsafe_allow_html=True,
        )

    with st.expander("Alert History"):
        render_alerts()

    with st.expander("Decision Detail"):
        detail_rows = []
        for param, status in evaluation.parameter_status.items():
            detail_rows.append({"parameter": param, "level": status.level, "reason": status.reason})
        st.table(pd.DataFrame(detail_rows))

    st.caption("Simulation ticks every second. Upload a CSV to replay recorded data.")

    if auto_refresh:
        time.sleep(REFRESH_MS / 1000)
        st.experimental_rerun()


if __name__ == "__main__":
    main()


