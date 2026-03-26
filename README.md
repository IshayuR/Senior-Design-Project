# Restaurant Lighting Control

Full-stack proof of concept for CSE Senior Design:

- React Native frontend with Expo Router
<<<<<<< HEAD
- FastAPI backend with SQLite persistence
=======
- FastAPI backend with built-in MQTT bridge and cron scheduler
- SQLite persistence layer
>>>>>>> 0108b824 (update README)
- AWS IoT Core integration via MQTT (paho-mqtt)
- Weekly and custom date scheduling with automatic light control
- ESP32 device simulator for end-to-end testing without hardware
- Repository/service abstraction for later MongoDB migration

---

## Architecture Overview

```text
Frontend (Expo / React Native)
    |
    |-- POST /lights/toggle -----------> Backend (FastAPI + SQLite)
    |                                       |-- Update SQLite
    |                                       |-- Publish MQTT "on"/"off"  --> AWS IoT --> ESP32
    |
    |-- POST /schedule/weekly ----------> Backend --> SQLite (weekly_schedule)
    |-- POST /schedule/custom ----------> Backend --> SQLite (custom_schedule)
    |
    |   [Built-in APScheduler - every minute]
    |   Check today's schedule in SQLite
    |   If time matches --> Publish MQTT --> AWS IoT --> ESP32
    |
    |-- GET /lights/status ------------> Backend --> SQLite
    |-- GET /lights/history -----------> Backend --> SQLite
    |-- GET /schedule/today -----------> Backend --> SQLite
```

### Frontend

- Path: `frontend/`
- Framework: Expo + React Native + Expo Router (TypeScript)
- Core state/data client: `frontend/lightingStore.tsx`
- Reads backend base URL from `EXPO_PUBLIC_API_BASE_URL`
- Screens: login, dashboard, schedule (weekly + custom dates), history, profile

### Backend

- Path: `backend/`
- Framework: FastAPI
- Entry point: `backend/app/main.py`
- Route module: `backend/app/routes/lights.py`
- Service layer: `backend/app/services/light_service.py`
- DB layer: `backend/app/database/db.py` (SQLite)
<<<<<<< HEAD
- On startup, connects to AWS IoT Core via MQTT
- Toggle endpoint publishes `on`/`off` commands to the ESP32

### AWS IoT Core (MQTT)

- Path: `aws/`
- MQTT client module: `aws/mqtt_client.py`
- ESP32 simulator: `aws/simulate_esp32.py`
- End-to-end test: `aws/test_connection.py`
- Certificates: `aws/certs/` (gitignored)
- Protocol: MQTT over TLS (port 8883) using X.509 mutual authentication
- Topics:
  - `esp32/ESP32_Device_01/cmd` — commands sent to the ESP32
  - `esp32/ESP32_Device_01/tele` — telemetry/status from the ESP32

### Data Flow

```
Frontend (toggle tap)
  → POST /lights/toggle
    → FastAPI updates SQLite
    → FastAPI publishes "on"/"off" to MQTT cmd topic
      → ESP32 (or simulator) receives command
      → ESP32 publishes "LOAD=ON"/"LOAD=OFF" to tele topic
        → Backend receives telemetry
```
=======
- MQTT bridge: `backend/app/mqtt_bridge.py` (connects to AWS IoT Core on startup)
- Scheduler: `backend/app/scheduler.py` (APScheduler cron job, checks schedules every minute)
>>>>>>> 0108b824 (update README)

### AWS IoT Core (MQTT)

- Path: `aws/`
- MQTT client module: `aws/mqtt_client.py`
- ESP32 simulator: `aws/simulate_esp32.py`
- End-to-end test: `aws/test_connection.py`
- Certificates: `aws/certs/` (gitignored)
- Protocol: MQTT over TLS (port 8883) using X.509 mutual authentication
- Topics:
  - `esp32/ESP32_Device_01/cmd` — commands sent to the ESP32
  - `esp32/ESP32_Device_01/tele` — telemetry/status from the ESP32

### Data Model

- `restaurant_lights`
  - `restaurant_id` (PK)
  - `state` (`on` / `off`)
  - `brightness` (`0-100`)
  - `schedule_on`, `schedule_off`
  - `last_updated`
- `light_history`
  - `id` (auto), `restaurant_id`, `action`, `timestamp`
- `weekly_schedule`
  - `id` (auto), `restaurant_id`, `day_of_week` (0=Mon..6=Sun)
  - `enabled`, `start_time`, `stop_time`, `updated_at`
  - Unique constraint: `(restaurant_id, day_of_week)`
- `custom_schedule`
  - `id` (auto), `restaurant_id`, `schedule_date` (YYYY-MM-DD)
  - `start_time`, `stop_time`, `updated_at`
  - Unique constraint: `(restaurant_id, schedule_date)`

---

## Repository Structure

```text
backend/
  app/
    main.py              FastAPI app, lifespan (DB + MQTT + scheduler)
    mqtt_bridge.py       Connects to AWS IoT, exposes publish_light_command()
    scheduler.py         APScheduler cron job, checks weekly/custom schedules
    routes/
      lights.py          All /lights/* endpoints
    models/
      light.py           Pydantic models for requests/responses
    services/
      light_service.py   Business logic, publishes MQTT on toggle
    database/
      db.py              SQLite schema and connection helper
  requirements.txt

frontend/
  app/
    _layout.tsx          Root layout with LightingProvider
    index.tsx            Login screen
    dashboard.tsx        Light toggle dashboard
    schedule.tsx         Weekly + custom date scheduling
    history.tsx          Action history log
    profile.tsx          Profile / logout
    BottomNav.tsx        Bottom navigation bar
  lightingStore.tsx      React context: API calls to backend
  package.json
  app.json
  .env.example

aws/
  mqtt_client.py         IoTMQTTClient class (TLS mutual auth)
  simulate_esp32.py      ESP32 device simulator
  test_connection.py     Automated MQTT round-trip test
  certs/                 (gitignored — certificates go here)
```

---

## Prerequisites

- Python `3.10+`
- Node.js `18+` and npm
- Expo Go app on phone (for physical device testing), or iOS/Android simulator
- AWS account with IoT Core access (for MQTT integration)

---

## Local Setup (First Time)

From repo root:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Install frontend packages:

```bash
cd frontend
npm install
cd ..
```

---

## Configure AWS IoT Core (MQTT)

1. Copy the environment template:

```bash
cp .env.example .env
```

2. Place the following certificate files in `aws/certs/`:
   - `AmazonRootCA1.pem` — Amazon Root CA
   - `backend-certificate.pem.crt` — backend client certificate
   - `backend-private.pem.key` — backend client private key
   - `esp32-certificate.pem.crt` — ESP32 device certificate
   - `esp32-private.pem.key` — ESP32 device private key

3. Verify `.env` has the correct endpoint and cert paths:

```env
AWS_IOT_ENDPOINT=a34pq72gp9sk70-ats.iot.us-east-1.amazonaws.com
AWS_IOT_CA_CERT=aws/certs/AmazonRootCA1.pem
AWS_IOT_BACKEND_CERT=aws/certs/backend-certificate.pem.crt
AWS_IOT_BACKEND_KEY=aws/certs/backend-private.pem.key
AWS_IOT_ESP32_CERT=aws/certs/esp32-certificate.pem.crt
AWS_IOT_ESP32_KEY=aws/certs/esp32-private.pem.key
```

Both certificates must have the IoT policy attached and be set to **Active** in the AWS IoT Core console.

---

## Configure Frontend API URL

Create `frontend/.env`:

```bash
cp frontend/.env.example frontend/.env
```

Set:

```env
EXPO_PUBLIC_API_BASE_URL=http://<YOUR_MACHINE_IP>:8000
```

Use the right value per target:

- Physical phone (Expo Go on same Wi-Fi): `http://<LAN_IP>:8000`
- iOS simulator: `http://127.0.0.1:8000`
- Android emulator: `http://10.0.2.2:8000`

Find your LAN IP with:

```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

---

## Run the Project

### Terminal 1: ESP32 Simulator

```bash
source venv/bin/activate
python -m aws.simulate_esp32
```

Start this first so it's ready when the backend connects. On startup the simulator publishes `boot` to the telemetry topic, then listens for `on`/`off` commands.

### Terminal 2: Backend

```bash
source venv/bin/activate
cd backend
uvicorn app.main:app --reload --host 0.0.0.0
```

On startup the backend connects to AWS IoT Core via MQTT. When you toggle lights from the frontend, the backend publishes `on`/`off` to the ESP32 cmd topic automatically.

If MQTT certs are not configured, the backend still runs — toggles just apply to the database only.

Backend URL: `http://127.0.0.1:8000`

### Terminal 2: Backend

```bash
source venv/bin/activate
cd backend && uvicorn app.main:app --reload --host 0.0.0.0
```

On startup the backend will:
1. Initialize SQLite (creates tables if needed)
2. Connect to AWS IoT Core via the MQTT bridge
3. Start the cron scheduler (checks schedules every minute)

Look for `MQTT bridge: connected to AWS IoT Core` in the logs.

Backend URL: `http://0.0.0.0:8000`

### Terminal 3: Frontend

```bash
cd frontend
npm start
```

Then:

- Scan QR code with Expo Go, or
- Press `i` for iOS simulator, or
- Press `a` for Android emulator

---

<<<<<<< HEAD
## Make-Style Command Shortcuts

Use these as quick copy/paste shortcuts (make-style workflow without requiring a `Makefile`).

### Setup

- `setup-python`
  ```bash
  python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
  ```
- `setup-frontend`
  ```bash
  cd frontend && npm install
  ```

### Run

- `run-simulator`
  ```bash
  source venv/bin/activate && python -m aws.simulate_esp32
  ```
- `run-backend`
  ```bash
  source venv/bin/activate && cd backend && uvicorn app.main:app --reload --host 0.0.0.0
  ```
- `run-frontend`
  ```bash
  cd frontend && npm start
  ```

### Test

- `test-api`
  ```bash
  curl http://127.0.0.1:8000/health && \
  curl "http://127.0.0.1:8000/lights/status?restaurantId=1" && \
  curl -X POST "http://127.0.0.1:8000/lights/toggle" -H "Content-Type: application/json" -d '{"restaurantId":1,"action":"toggle"}' && \
  curl "http://127.0.0.1:8000/lights/history?restaurantId=1"
  ```
- `test-mqtt` (requires simulator running in another terminal)
  ```bash
  source venv/bin/activate && python -m aws.test_connection
  ```

### Stop

- `stop-backend`
  ```bash
  lsof -ti :8000 | xargs kill -9
  ```
- `stop-frontend`
  ```bash
  lsof -ti :8081 | xargs kill -9
  ```

---

## API Endpoints

- `GET /health` — returns `{"status": "ok", "mqtt": "connected"|"disconnected"}`
- `GET /lights/status?restaurantId=1`
- `POST /lights/toggle` — toggles DB state and sends MQTT command to ESP32
- `POST /lights/schedule`
- `GET /lights/history`
=======
## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/lights/status?restaurantId=1` | Current light state |
| `POST` | `/lights/toggle` | Toggle light on/off (also publishes MQTT) |
| `POST` | `/lights/schedule` | Set simple schedule on/off times |
| `POST` | `/lights/schedule/weekly` | Upsert weekly schedule (per day of week) |
| `POST` | `/lights/schedule/custom` | Upsert custom date overrides |
| `GET` | `/lights/schedule/today?restaurantId=1` | Today's effective schedule |
| `GET` | `/lights/history?restaurantId=1` | Action history log |
>>>>>>> 0108b824 (update README)

Example payloads:

```json
// POST /lights/toggle
{ "restaurantId": 1, "action": "toggle" }

// POST /lights/schedule
{ "restaurantId": 1, "scheduleOn": "18:00", "scheduleOff": "23:30" }

// POST /lights/schedule/weekly
{
  "restaurantId": 1,
  "days": [
    { "dayOfWeek": 0, "enabled": true, "start": "18:00", "stop": "23:30" },
    { "dayOfWeek": 1, "enabled": true, "start": "18:00", "stop": "23:30" }
  ]
}

// POST /lights/schedule/custom
{
  "restaurantId": 1,
  "dates": [
    { "date": "2025-12-25", "start": "17:00", "stop": "23:59" }
  ]
}
```

Interactive API docs available at `http://127.0.0.1:8000/docs`.

---

## Scheduling

The backend includes a built-in cron scheduler (APScheduler) that runs every minute:

1. Checks `custom_schedule` for a matching date (highest priority)
2. Falls back to `weekly_schedule` for today's day of week
3. If the current time (`HH:MM`) matches `start_time`, publishes `on` via MQTT
4. If it matches `stop_time`, publishes `off` via MQTT

Day-of-week mapping: Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4, Saturday=5, Sunday=6.

Custom date schedules override the weekly schedule when dates match.

---

## Quick Backend Smoke Tests (curl)

```bash
# Health check
curl http://127.0.0.1:8000/health

# Light status
curl "http://127.0.0.1:8000/lights/status?restaurantId=1"

# Toggle light (triggers MQTT publish to ESP32)
curl -X POST http://127.0.0.1:8000/lights/toggle \
  -H "Content-Type: application/json" \
  -d '{"restaurantId":1,"action":"toggle"}'

# Set weekly schedule
curl -X POST http://127.0.0.1:8000/lights/schedule/weekly \
  -H "Content-Type: application/json" \
  -d '{"restaurantId":1,"days":[{"dayOfWeek":3,"enabled":true,"start":"18:00","stop":"23:30"}]}'

# Check today's schedule
curl "http://127.0.0.1:8000/lights/schedule/today?restaurantId=1"

# View history
curl "http://127.0.0.1:8000/lights/history?restaurantId=1"
```

---

## Manual End-to-End Test Flow

<<<<<<< HEAD
### Frontend ↔ Backend ↔ ESP32

1. Start the simulator (Terminal 1), backend (Terminal 2), and frontend (Terminal 3).
2. On Dashboard, tap the bulb to toggle lights.
3. Confirm the frontend state changes immediately.
4. Check Terminal 1 (simulator) — it should show the received command and published response.
5. Open History tab and verify the new event appears.

### MQTT Only (without frontend)

1. Start the simulator: `python -m aws.simulate_esp32`
2. In a second terminal run: `python -m aws.test_connection`
3. Confirm output shows `ALL TESTS PASSED (2/2)`

Alternatively, use the **AWS IoT MQTT Test Console**:

1. Subscribe to `esp32/ESP32_Device_01/tele`
2. Publish `on` to `esp32/ESP32_Device_01/cmd`
3. Confirm `LOAD=ON` appears on the tele subscription
4. Publish `off` and confirm `LOAD=OFF`
=======
### Frontend to Backend to ESP32

1. Start the simulator, backend, and frontend (see Run the Project above).
2. Open the app and login.
3. On Dashboard, tap the bulb to toggle lights.
4. Watch the backend logs for `MQTT bridge: published 'on'`.
5. Watch the simulator for `Received cmd <- 'on'` and `LOAD=ON`.
6. Toggle again and confirm `off` / `LOAD=OFF`.
7. Open History and verify events appear.
>>>>>>> 0108b824 (update README)

### Scheduling

1. Go to Schedule, switch to the Weekly tab.
2. Enable a day, set start/stop times, tap "Apply weekly schedule".
3. Or switch to Custom dates, add a specific date entry, tap "Save specific dates".
4. Verify with: `curl "http://127.0.0.1:8000/lights/schedule/today?restaurantId=1"`
5. When the current time matches a scheduled start/stop, the scheduler publishes MQTT automatically.

### MQTT Round-Trip Test

1. Start the simulator: `python -m aws.simulate_esp32`
2. In a second terminal run: `python -m aws.test_connection`
3. Confirm output shows `ALL TESTS PASSED (2/2)`

### AWS IoT Console Verification

1. Open the [AWS IoT MQTT Test Client](https://console.aws.amazon.com/iot/home?region=us-east-1#/test) (us-east-1).
2. Subscribe to `esp32/ESP32_Device_01/tele` and `esp32/ESP32_Device_01/cmd`.
3. Toggle a light from the app — you should see `on`/`off` on the cmd topic and `LOAD=ON`/`LOAD=OFF` on the tele topic.
4. You can also publish `on` or `off` to `esp32/ESP32_Device_01/cmd` directly from the console.

### Database Verification

```bash
sqlite3 backend/app/database/lights.db "SELECT * FROM restaurant_lights; SELECT '---'; SELECT * FROM light_history ORDER BY timestamp DESC LIMIT 5; SELECT '---'; SELECT * FROM weekly_schedule;"
```

---

## Make-Style Command Shortcuts

### Setup

```bash
# setup-python
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# setup-frontend
cd frontend && npm install
```

### Run

```bash
# run-simulator
source venv/bin/activate && python -m aws.simulate_esp32

# run-backend
source venv/bin/activate && cd backend && uvicorn app.main:app --reload --host 0.0.0.0

# run-frontend
cd frontend && npm start
```

### Test

```bash
# test-api
curl http://127.0.0.1:8000/health && \
curl "http://127.0.0.1:8000/lights/status?restaurantId=1" && \
curl -X POST http://127.0.0.1:8000/lights/toggle -H "Content-Type: application/json" -d '{"restaurantId":1,"action":"toggle"}' && \
curl "http://127.0.0.1:8000/lights/history?restaurantId=1"

# test-mqtt (requires simulator running)
source venv/bin/activate && python -m aws.test_connection
```

### Stop

```bash
# stop-backend
lsof -ti :8000 | xargs kill -9

# stop-frontend
lsof -ti :8081 | xargs kill -9
```

---

## Stopping Running Services

- In any terminal: `Ctrl + C`

If a port is stuck:

```bash
lsof -i :8000
kill -9 <PID>
```

```bash
lsof -i :8081
kill -9 <PID>
```
