# Industrial Worker Safety Monitoring Web Application (Software-Only)

A full-stack Flask + SQLite simulation of an AI-powered wearable safety monitor for industrial workers. Meets SIH/patent-style requirements with deterministic fusion logic, alerting, admin/worker UIs, demo scenarios, and daily reports.

## Features
- Virtual sensor input: manual entry from worker UI or CSV-driven demo runner.
- Deterministic fusion decision engine with weighted risks and safety-first overrides.
- Alerts with cooldown, escalation after 60s, acknowledge/resolve flows.
- Two-way messaging: admin -> worker (with optional STOP WORK command) and worker acknowledgements.
- Unconscious detection via inactivity timeout (45s).
- Zone sensitivity for gas/SpO₂ risk (NORMAL, CHEMICAL, MINING, FIRE-RESCUE).
- Admin dashboard with charts, alerts, messaging, and report export.
- Worker console with big status tile, hazard buttons, panic button, and message acknowledgements.
- Demo scenarios replay script and sample CSVs.
- Simple unit tests for decision engine and alert cooldowns.

## Project Structure
```
backend/                Flask app, routes, decision engine, alerts, models
templates/              HTML templates (worker.html, admin.html)
static/css, static/js   Frontend styling and logic
demo_data/              Sample CSV scenarios
scripts/demo_runner.py  Replays scenarios against running server
tests/                  Pytest suites
config.py               App/config knobs (zones, timeouts)
requirements.txt        Python deps
run.sh / Procfile       Launch helpers
```

## Setup
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export FLASK_APP=backend
flask run --host=0.0.0.0 --port=5000
```

Windows (PowerShell):
```powershell
# from project folder
.venv\Scripts\Activate.ps1
./run.ps1            # starts Flask (FLASK_APP=backend)
```

Editable install (optional):
```bash
# make project importable from parent folders and install deps
pip install -e .
``` 
Or use `./run.sh` (Linux/macOS) or `Procfile` (Heroku-style).

## Default Credentials (seeded)
- Admin: `admin` / `admin123`
- Worker: worker_id `W-001`, PIN `1234`

## Using the App
- Worker UI: open `http://localhost:5000/`  
  - Login with worker ID + PIN.  
  - Enter vitals, tap **Send Reading**.  
  - Hazard buttons fire emergency alerts.  
  - **EMERGENCY HELP** sends manual emergency.  
  - Messages show in the Messages panel; acknowledge to clear.
- Admin UI: open `http://localhost:5000/admin`  
  - Login as admin.  
  - Left: worker cards. Click to load detail & last 6 min chart.  
  - Right: alert center (ack/resolve), message composer (+ optional STOP WORK), report generator.

## Decision Engine (summary)
- Clamps inputs; maps fatigue strings to 0/1/2.
- Per-parameter risks per spec; gas/SpO₂ scaled by zone sensitivity (factor).  
- Weighted fusion: health (HR/SpO₂/Temp) 0.35, gas 0.35, fatigue 0.30.  
- Overrides: Gas+Low O₂, Fatigue+High HR, Heat Stress, multiple high risks, any risk ≥95 -> emergency.  
- Status: 0–40 SAFE, 41–70 WARNING, 71–100 EMERGENCY.  
- Transparent reasons returned in API.

## API Highlights
- Auth: `POST /login/admin`, `POST /login/worker`
- Worker: `GET /worker/profile`, `POST /worker/reading`, `POST /worker/hazard`, `POST /worker/emergency`, `POST /worker/poll`, `POST /worker/ack_message`
- Admin: `GET /admin/workers`, `GET /admin/worker/<id>/history?minutes=6`, `GET /admin/alerts`, `POST /admin/message`, `POST /admin/ack_alert`, `POST /admin/resolve_alert`, `POST /admin/action`, `GET /admin/report/daily?date=YYYY-MM-DD`

## Reports
- Daily summary CSV: `worker_id,date,total_readings,total_alerts,avg_hr,avg_spo2,avg_temp,avg_gas,%safe,%warning,%emergency`
- Alerts CSV: timestamp, worker_id, alert_type, priority, reason, acknowledged_by, resolved.

## Demo Scenarios
Run while server is up:
```bash
python scripts/demo_runner.py
```
Scenarios (1s per row):
- `scenario_normal.csv`: stays SAFE.
- `scenario_warning_spo2.csv`: gradual SpO₂ drop → WARNING then EMERGENCY.
- `scenario_gas_spike.csv`: gas 800 + SpO₂ dip → Gas + Low O₂ emergency.
- `scenario_fatigue_collapse.csv`: fatigue high + HR spike → emergency.

## Testing
```bash
pytest
```

## Config knobs (config.py)
- `ZONE_SENSITIVITY`, `INACTIVITY_TIMEOUT`, `ALERT_COOLDOWN`, `ESCALATE_AFTER_SECONDS`, `RATE_LIMIT_READINGS_PER_SEC`.

## Safety Notes
- Passwords stored as bcrypt hashes; sessions secured via Flask secret key.
- Rate-limited worker readings (2/sec default).
- Alerts favor fail-safe escalation; unconscious detection creates emergency after inactivity.

