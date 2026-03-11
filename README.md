# Restaurant Lighting Control

Full-stack proof of concept for CSE Senior Design:

- React Native frontend with Expo Router
- FastAPI backend
- SQLite persistence layer (repository abstraction for later MongoDB migration)
- AWS IoT Core integration via MQTT (paho-mqtt)
- ESP32 device simulator for end-to-end testing without hardware

---

## Architecture Overview

### Frontend

- Path: `frontend/`
- Framework: Expo + React Native + Expo Router (TypeScript)
- Core state/data client: `frontend/lightingStore.tsx`
- Reads backend base URL from `EXPO_PUBLIC_API_BASE_URL`

### Backend

- Path: `backend/`
- Framework: FastAPI
- Entry point: `backend/app/main.py`
- Route module: `backend/app/routes/lights.py`
- Service layer: `backend/app/services/light_service.py`
- DB layer: `backend/app/database/db.py` (SQLite)

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

### Data Model (Prototype)

- `restaurant_lights`
  - `restaurant_id` (PK)
  - `state` (`on` / `off`)
  - `brightness` (`0-100`)
  - `schedule_on`
  - `schedule_off`
  - `last_updated`
- `light_history`
  - `id` (auto)
  - `restaurant_id`
  - `action`
  - `timestamp`

---

## Repository Structure

```text
backend/
  app/
    main.py
    routes/
      lights.py
    models/
      light.py
    services/
      light_service.py
    database/
      db.py
  requirements.txt

frontend/
  app/
    _layout.tsx
    index.tsx
    dashboard.tsx
    schedule.tsx
    history.tsx
    profile.tsx
    BottomNav.tsx
  assets/
    budderfly_logo.png
    budderfly_logo.svg
  lightingStore.tsx
  index.ts
  package.json
  app.json
  .env.example

aws/
  mqtt_client.py
  simulate_esp32.py
  test_connection.py
  certs/            (gitignored — certificates go here)
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

---

## Run the Project

### Terminal 1: Backend

```bash
source venv/bin/activate
cd backend
uvicorn app.main:app --reload
```

If file-watcher issues appear in your environment:

```bash
uvicorn app.main:app
```

Backend URL: `http://127.0.0.1:8000`

### Terminal 2: ESP32 Simulator (optional — for MQTT testing)

```bash
source venv/bin/activate
python -m aws.simulate_esp32
```

On startup the simulator publishes `boot` to the telemetry topic, then listens for `on`/`off` commands.

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

- `run-backend`
  ```bash
  source venv/bin/activate && cd backend && uvicorn app.main:app --reload
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

- `GET /health`
- `GET /lights/status?restaurantId=1`
- `POST /lights/toggle`
- `POST /lights/schedule`
- `GET /lights/history`

Example payloads:

```json
{
  "restaurantId": 1,
  "action": "toggle"
}
```

```json
{
  "restaurantId": 1,
  "scheduleOn": "18:00",
  "scheduleOff": "23:30"
}
```

---

## Quick Backend Smoke Tests (curl)

```bash
curl http://127.0.0.1:8000/health
curl "http://127.0.0.1:8000/lights/status?restaurantId=1"
curl -X POST "http://127.0.0.1:8000/lights/toggle" \
  -H "Content-Type: application/json" \
  -d '{"restaurantId":1,"action":"toggle"}'
curl -X POST "http://127.0.0.1:8000/lights/schedule" \
  -H "Content-Type: application/json" \
  -d '{"restaurantId":1,"scheduleOn":"18:00","scheduleOff":"23:30"}'
curl "http://127.0.0.1:8000/lights/history?restaurantId=1"
```

---

## Manual End-to-End Test Flow

### Frontend ↔ Backend

1. Open app and login.
2. On Dashboard, tap bulb to toggle lights.
3. Confirm status changes immediately.
4. Open History and verify new event appears.
5. Open Schedule, change times, apply schedule.
6. Recheck status/history and confirm backend updates persisted.

### MQTT (Backend ↔ ESP32)

1. Start the simulator: `python -m aws.simulate_esp32`
2. In a second terminal run: `python -m aws.test_connection`
3. Confirm output shows `ALL TESTS PASSED (2/2)`

Alternatively, use the **AWS IoT MQTT Test Console**:

1. Subscribe to `esp32/ESP32_Device_01/tele`
2. Publish `on` to `esp32/ESP32_Device_01/cmd`
3. Confirm `LOAD=ON` appears on the tele subscription
4. Publish `off` and confirm `LOAD=OFF`

---

## Stopping Running Services

- In backend terminal: `Ctrl + C`
- In frontend terminal: `Ctrl + C`

If a port is stuck:

```bash
lsof -i :8000
kill -9 <PID>
```

```bash
lsof -i :8081
kill -9 <PID>
```

---

## MongoDB Migration Notes (Later Phase)

SQLite is used intentionally for zero-setup local iteration.

To migrate without refactoring business logic:

- Keep `backend/app/routes/lights.py` unchanged.
- Keep `backend/app/services/light_service.py` unchanged.
- Implement a MongoDB repository that matches `LightRepository`.
- Replace dependency wiring from `SQLiteLightRepository` to Mongo repository.

---

## Out of Scope (Current Phase)

- Schedule-based MQTT control (separate branch)
- Auth/authz
- Encryption hardening
- Deployment/infrastructure automation
