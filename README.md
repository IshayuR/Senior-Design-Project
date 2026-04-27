# Restaurant Lighting Control

Full-stack proof of concept for CSE Senior Design:

- React Native frontend with Expo Router
- FastAPI backend with built-in MQTT bridge and cron scheduler
- SQLite persistence layer
- AWS IoT Core integration via MQTT (paho-mqtt)
- Weekly and custom date scheduling with automatic light control
- ESP32 device simulator for end-to-end testing without hardware
- Local SQLite-backed login for development

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
- MQTT bridge: `backend/app/mqtt_bridge.py` (connects to AWS IoT Core on startup)
- Scheduler: `backend/app/scheduler.py` (APScheduler cron job, checks schedules every minute)

### AWS IoT Core (MQTT)

- Path: `aws/`
- MQTT client module: `aws/mqtt_client.py`
- ESP32 simulator: `aws/simulate_esp32.py`
- End-to-end test: `aws/test_connection.py`
- Certificates: `aws/certs/` (gitignored)
- Protocol: MQTT over TLS (port 8883) using X.509 mutual authentication
- Topics:
  - `esp32/ESP32_Device_01/cmd` — commands sent to the ESP32
  - `esp32/ESP32_Device_01/schedule` — firmware-native schedule payload
  - `esp32/ESP32_Device_01/tele` — JSON telemetry from the ESP32
  - `esp32/ESP32_Device_01/status` — JSON status/health messages from the ESP32

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
- `users`
  - `id` (auto), `email`, `name`, `password_hash`, `restaurant_id`, `created_at`
  - Used for local development login

### Data Flow

```text
Frontend (toggle tap)
  --> POST /lights/toggle
    --> FastAPI updates SQLite
    --> FastAPI publishes "ON"/"OFF" to MQTT cmd topic
      --> ESP32 (or simulator) receives command
      --> ESP32 publishes JSON status + JSON telemetry
        --> Backend receives device snapshot and syncs SQLite/UI state

Frontend (schedule save)
  --> POST /lights/schedule or /lights/schedule/weekly or /lights/schedule/custom
    --> FastAPI updates SQLite schedule tables
    --> FastAPI converts today's "on window" into firmware "off block" JSON
      --> Publishes to esp32/ESP32_Device_01/schedule
        --> ESP32 switches back to AUTO mode and runs its own local schedule
```

### Integration Contract

- AWS account/endpoint priority:
  - The backend loads `AWS_IOT_ENDPOINT` from `.env`.
  - The ECE firmware in [`ece-files/controller.ino`](./ece-files/controller.ino) is now aligned to the same `us-east-1` endpoint already configured in this repo.
- Device command priority:
  - The backend now sends the firmware's exact command values: `ON`, `OFF`, `AUTO`, `DEMO`.
- Device schedule priority:
  - The backend now publishes the firmware's exact 6-block JSON schedule format on `esp32/<device_id>/schedule`.
  - The app still stores schedules as user-friendly "lights ON from `start` to `stop`".
  - The backend converts that into the firmware's `schedule_type=off_blocks` contract before publishing.
- Device state priority:
  - The backend now listens to both `.../tele` and `.../status` and treats the device as the source of truth for the current load state when telemetry arrives.

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
AWS_IOT_DEVICE_ID=ESP32_Device_01
AWS_IOT_CA_CERT=aws/certs/AmazonRootCA1.pem
AWS_IOT_BACKEND_CERT=aws/certs/backend-certificate.pem.crt
AWS_IOT_BACKEND_KEY=aws/certs/backend-private.pem.key
AWS_IOT_ESP32_CERT=aws/certs/esp32-certificate.pem.crt
AWS_IOT_ESP32_KEY=aws/certs/esp32-private.pem.key
```

Both certificates must have the IoT policy attached and be set to **Active** in the AWS IoT Core console.

### MQTT Contract Used By The Integrated Project

- `esp32/ESP32_Device_01/cmd`
  - Accepted commands: `ON`, `OFF`, `AUTO`, `DEMO`
- `esp32/ESP32_Device_01/schedule`
  - JSON payload with `s1_en`, `s1_start_h`, `s1_start_m`, `s1_end_h`, `s1_end_m`, ... through `s6_*`
  - These are firmware "off blocks", not "on blocks"
- `esp32/ESP32_Device_01/status`
  - Firmware publishes JSON like `{"device":"ESP32_Device_01","status":"manual_on","ip":"...","uptime":123}`
- `esp32/ESP32_Device_01/tele`
  - Firmware publishes JSON telemetry including `load` and `mode`

### AWS Access For The ECE Team

There are two different access paths, and both matter here:

1. IAM access for the AWS Console MQTT test client
2. X.509 certificates for this repo's Python backend/simulator and the physical ESP32

IAM access alone is not enough for this codebase's TLS MQTT clients. AWS documents that AWS IoT supports IAM and X.509 identities, and device connections in practice commonly use X.509 certificates while desktop/web apps can use IAM-backed access.

#### Part A: Give the ECE team AWS console access to your MQTT test client

1. In AWS IAM, create a user for each teammate or use IAM Identity Center.
2. Give them console access and tell them to use region `us-east-1`.
3. Attach these AWS managed policies to that IAM identity:
   - `AWSIoTConfigAccess`
   - `AWSIoTDataAccess`
4. Share the account sign-in URL, username, and their temporary password.
5. They can then open AWS IoT Core > MQTT test client and subscribe to:
   - `esp32/ESP32_Device_01/#`
6. To manually drive the device from the AWS console, publish to:
   - Topic: `esp32/ESP32_Device_01/cmd`
   - Payload: `ON` or `OFF`
7. To watch the device state, keep subscriptions open on:
   - `esp32/ESP32_Device_01/tele`
   - `esp32/ESP32_Device_01/status`

#### Part B: Let them run this repo locally on their laptop

1. In your AWS account, create or reuse an IoT Thing for the Python backend client.
2. Create/download a certificate and private key for that backend client.
3. Attach an IoT policy that allows:
   - `iot:Connect`
   - `iot:Publish`
   - `iot:Subscribe`
   - `iot:Receive`
4. Scope the topic resources to:
   - `esp32/ESP32_Device_01/cmd`
   - `esp32/ESP32_Device_01/schedule`
   - `esp32/ESP32_Device_01/tele`
   - `esp32/ESP32_Device_01/status`
5. Attach that IoT policy to the certificate.
6. Attach the certificate to the Thing.
7. Give the teammate these non-secret/non-rotating values:
   - `AWS_IOT_ENDPOINT`
   - `AWS_IOT_DEVICE_ID`
   - `AmazonRootCA1.pem`
8. Give them the backend cert/key pair securely for local testing only:
   - `backend-certificate.pem.crt`
   - `backend-private.pem.key`
9. If they need to run `aws/simulate_esp32.py`, also give them a second cert/key pair for the simulated device:
   - `esp32-certificate.pem.crt`
   - `esp32-private.pem.key`
10. They should place those files in `aws/certs/`, copy `.env.example` to `.env`, and update the paths if needed.

#### Recommended IoT policy shape for the repo

Use your real AWS account ID in place of `123456789012`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["iot:Connect"],
      "Resource": [
        "arn:aws:iot:us-east-1:123456789012:client/backend_server_01",
        "arn:aws:iot:us-east-1:123456789012:client/backend_test_runner",
        "arn:aws:iot:us-east-1:123456789012:client/ESP32_Device_01"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["iot:Publish", "iot:Receive"],
      "Resource": [
        "arn:aws:iot:us-east-1:123456789012:topic/esp32/ESP32_Device_01/cmd",
        "arn:aws:iot:us-east-1:123456789012:topic/esp32/ESP32_Device_01/schedule",
        "arn:aws:iot:us-east-1:123456789012:topic/esp32/ESP32_Device_01/tele",
        "arn:aws:iot:us-east-1:123456789012:topic/esp32/ESP32_Device_01/status"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["iot:Subscribe"],
      "Resource": [
        "arn:aws:iot:us-east-1:123456789012:topicfilter/esp32/ESP32_Device_01/cmd",
        "arn:aws:iot:us-east-1:123456789012:topicfilter/esp32/ESP32_Device_01/schedule",
        "arn:aws:iot:us-east-1:123456789012:topicfilter/esp32/ESP32_Device_01/tele",
        "arn:aws:iot:us-east-1:123456789012:topicfilter/esp32/ESP32_Device_01/status"
      ]
    }
  ]
}
```

### Exact AWS Console/CLI Steps To Wire Up Repo Certificates

Console flow:

1. AWS IoT Core > Manage > All devices > Things > Create thing
2. AWS IoT Core > Security > Policies > Create policy
3. AWS IoT Core > Security > Certificates > Create certificate
4. Download the cert and private key
5. On that certificate, choose `Attach policy`
6. On that certificate, choose `Attach thing`
7. Make sure the certificate status is `Active`

CLI flow:

```bash
aws iot attach-policy --policy-name <YOUR_POLICY_NAME> --target <CERTIFICATE_ARN>
aws iot attach-thing-principal --thing-name <YOUR_THING_NAME> --principal <CERTIFICATE_ARN>
```

### Local End-To-End Test Flow

1. Start the simulated device:

```bash
source venv/bin/activate
python -m aws.simulate_esp32
```

2. Start the backend:

```bash
source venv/bin/activate
uvicorn backend.app.main:app --reload
```

3. In another terminal, run the MQTT round-trip test:

```bash
source venv/bin/activate
python -m aws.test_connection
```

4. Expected result:
   - The test publishes `ON` and `OFF`
   - The simulator responds on `.../status` and `.../tele`
   - The backend tracks device-reported load state

If the physical ESP32 is already online with client ID `ESP32_Device_01`, the simulator will repeatedly disconnect because AWS IoT only allows one active connection per MQTT client ID. For simulator-based testing, either power off the physical device first or provision a separate test Thing/certificate/device ID.

### Important Security Note

The file `ece-files/certs.h` currently contains an embedded private key and certificate material. If those credentials are real and not throwaway test creds, rotate them in AWS IoT Core and replace the file with newly issued credentials before wider sharing.

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
python main.py
```

On startup the backend connects to AWS IoT Core via MQTT. When you toggle lights from the frontend, the backend publishes `on`/`off` to the ESP32 cmd topic automatically.

If MQTT certs are not configured, the backend still runs — toggles just apply to the database only.

Backend URL: `http://127.0.0.1:8000`

### Terminal 3: Frontend

```bash
cd frontend
npx expo start -c
```

Then:

- Scan QR code with Expo Go, or
- Press `i` for iOS simulator, or
- Press `a` for Android emulator

---

## ECE Integration Demo Runbook

This is the exact order to follow if you need to prove that the mobile app, backend, AWS IoT, and the ECE device are all working together live.

### What Must Already Match

Before demo day, confirm all of these are true:

1. The backend `.env` and the ESP32 firmware point at the same AWS IoT endpoint:
   - `a34pq72gp9sk70-ats.iot.us-east-1.amazonaws.com`
2. The backend and the ESP32 use the same device ID:
   - `ESP32_Device_01`
3. The backend and the ESP32 use the same MQTT topics:
   - `esp32/ESP32_Device_01/cmd`
   - `esp32/ESP32_Device_01/schedule`
   - `esp32/ESP32_Device_01/tele`
   - `esp32/ESP32_Device_01/status`
4. Both the backend certificate and the device certificate are `Active` in AWS IoT Core and both have permission to connect, publish, subscribe, and receive on those four topics.
5. Only one physical device is online with client ID `ESP32_Device_01`.
   - Do not run `aws/simulate_esp32.py` during the live hardware demo.
6. The phone running Expo Go and the laptop running the backend can reach each other on the same network if you are using a physical phone.
7. The ESP32 has working Wi-Fi credentials stored and has internet access.
8. The ESP32 clock is able to sync via NTP.
9. The device is being demoed in U.S. Eastern time.
   - The firmware hardcodes `EST5EDT,M3.2.0/2,M11.1.0/2`.
   - The frontend time-zone dropdown is not currently wired into backend or firmware behavior, so do not rely on it to change device time.

### Step 1: Verify AWS and Device Without the App

Do this first so you can isolate hardware/AWS issues before involving the frontend.

1. Power on the ESP32.
2. Open its serial monitor.
3. Wait for:
   - Wi-Fi connection success
   - `Connecting to AWS...`
   - `AWS Connected!`
4. In AWS IoT Core, open MQTT test client.
5. Subscribe to:
   - `esp32/ESP32_Device_01/#`
6. Confirm you see device status messages such as:
   - `boot`
   - `online`
7. Publish `ON` to:
   - `esp32/ESP32_Device_01/cmd`
8. Confirm all three of these happen:
   - The physical light/load turns on
   - AWS receives a status payload with `manual_on`
   - AWS receives telemetry with `"load":1`
9. Publish `OFF` to the same command topic.
10. Confirm all three of these happen:
   - The physical light/load turns off
   - AWS receives a status payload with `manual_off`
   - AWS receives telemetry with `"load":0`

If this step fails, stop there. The issue is on the AWS, certificate, topic, or ECE device side, not the mobile app side.

### Step 2: Start the App Stack

1. In the repo root, make sure `.env` contains the backend AWS endpoint, device ID, and backend cert paths.
2. In `frontend/.env`, set:
   - `EXPO_PUBLIC_API_BASE_URL=http://<your-laptop-LAN-IP>:8000`
3. Start the backend:

```bash
source venv/bin/activate
python main.py
```

4. Watch the backend logs and confirm you see a successful MQTT connection.
5. Start the frontend:

```bash
cd frontend
npx expo start -c
```

6. Open the app on the phone or simulator and log in with:
   - `wei.wei@uconn.edu`
   - `password123`
7. Open the dashboard screen.
8. Confirm the bulb icon loads and the `Updated:` timestamp is refreshing when status changes.

### Step 3: Prove App Toggle -> AWS -> Device -> App Icon

This is the main end-to-end proof for the live demo.

1. Make sure the bulb is currently off.
2. Tap the bulb icon once.
3. Immediately verify this chain:
   - The backend receives `POST /lights/toggle`
   - The backend publishes `ON` to `esp32/ESP32_Device_01/cmd`
   - AWS MQTT test client shows the command and then the device reply
   - The ESP32 turns the load on
   - The device publishes `manual_on`
   - The device publishes telemetry with `"load":1`
   - Within about 1-5 seconds, the app dashboard refreshes and the bulb shows `On`
4. Tap the bulb icon again.
5. Verify the same chain in reverse:
   - Backend publishes `OFF`
   - Device turns off
   - Device publishes `manual_off`
   - Telemetry shows `"load":0`
   - The app bulb changes to `Off`

Important: the dashboard polls backend status every second, and the ESP32 telemetry publishes every 5 seconds. The icon is not an instant hardware interrupt; give it a few seconds to settle before speaking over it in the demo.

### Step 4: Prove Scheduling Works

For this codebase, scheduling is enforced by the ESP32 after the backend sends the current day's schedule payload. The backend is not currently firing `ON` and `OFF` at schedule boundaries itself.

Use this exact demo method:

1. In the app, open `Schedule`.
2. Use `Custom dates` for the cleanest demo.
3. Add today's date.
4. Pick a time window that includes the current Eastern time if you want the effect to happen immediately.
   - Example: if it is `2:10 PM ET`, set start `14:09` and stop `14:12`.
5. Save the custom date schedule.
6. In AWS MQTT test client, confirm the device receives a payload on:
   - `esp32/ESP32_Device_01/schedule`
7. Confirm the device publishes status:
   - `schedule_updated`
8. Confirm the device has returned to automatic mode.
   - You should see telemetry with `"mode":"auto"`
9. Confirm the physical light matches what the schedule says should happen right now.
   - If current time is inside the configured ON window, the load should turn on shortly after the schedule update.
   - If current time is outside the configured ON window, the load should remain off.
10. If you want to prove an actual automatic transition, set the stop time 1-2 minutes in the future and wait for the boundary.
11. At the boundary, confirm:
   - The ESP32 changes the load state on its own
   - Telemetry updates
   - The app bulb icon updates on the next refresh cycle

### Step 5: What You Need to Watch During the Live Demo

Have these four views open at once if possible:

1. The mobile app dashboard
2. The AWS IoT MQTT test client subscribed to `esp32/ESP32_Device_01/#`
3. The backend terminal logs
4. The ESP32 hardware or serial monitor

That gives you a clean explanation path:

1. App sent request
2. Backend published MQTT
3. Device received it
4. Device reported state back
5. App icon updated from the synchronized state

### Conditions Required for the Demo to Work Live

All of these must go right:

1. AWS IoT certificates are active and not expired or detached.
2. The backend machine has the correct `.env` and readable certificate files.
3. The ESP32 has the correct certificate and private key compiled into `ece-files/certs.h`.
4. The backend and device agree on endpoint, device ID, and topics.
5. The ESP32 has Wi-Fi and internet access at the demo location.
6. The phone can reach the backend URL in `frontend/.env`.
7. No second device or simulator is connected with MQTT client ID `ESP32_Device_01`.
8. The device time is correct and in Eastern time for schedule demos.
9. You leave a few seconds for telemetry and UI polling to catch up after each action.

### Fast Failure Isolation

If something breaks, identify the failing link quickly:

- App button changes nothing and backend sees no request:
  - Frontend cannot reach the backend URL.
- Backend gets the request but AWS shows nothing:
  - Backend MQTT connection or backend cert/policy issue.
- AWS shows `ON` or `OFF` but hardware does nothing:
  - ECE firmware, device cert, topic subscription, or device connectivity issue.
- Hardware changes but app icon does not:
  - Device telemetry/status is not getting back to backend, or you did not wait for the next poll/telemetry cycle.
- Schedule saves but device does not behave automatically:
  - Time zone mismatch, bad current-day schedule selection, or device did not receive `schedule_updated`.

---

## API Endpoints

| Method | Path                                    | Description                               |
| ------ | --------------------------------------- | ----------------------------------------- |
| `GET`  | `/health`                               | Health check                              |
| `POST` | `/auth/login`                           | Local development login                   |
| `GET`  | `/lights/status?restaurantId=1`         | Current light state                       |
| `POST` | `/lights/toggle`                        | Toggle light on/off (also publishes MQTT) |
| `POST` | `/lights/schedule`                      | Set simple schedule on/off times          |
| `POST` | `/lights/schedule/weekly`               | Upsert weekly schedule (per day of week)  |
| `POST` | `/lights/schedule/custom`               | Upsert custom date overrides              |
| `GET`  | `/lights/schedule/today?restaurantId=1` | Today's effective schedule                |
| `GET`  | `/lights/history?restaurantId=1`        | Action history log                        |

Example payloads:

```jsonc
// POST /auth/login
{ "email": "wei.wei@uconn.edu", "password": "password123" }

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

Local dev login:

- Email: `wei.wei@uconn.edu`
- Password: `password123`

---

## Scheduling

The backend includes a built-in cron scheduler (APScheduler) that runs every minute, but its current job is to sync the effective schedule for the day to the device. The ESP32 then enforces that schedule locally.

1. Checks `custom_schedule` for a matching date (highest priority)
2. Falls back to `weekly_schedule` for today's day of week
3. Converts the app's single ON window into the firmware's 6-block `off_blocks` JSON payload
4. Publishes that payload to `esp32/ESP32_Device_01/schedule`
5. The ESP32 switches to auto mode when it accepts the schedule and then changes the load locally based on its own clock

Day-of-week mapping: Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4, Saturday=5, Sunday=6.

Custom date schedules override the weekly schedule when dates match.

Important demo note: schedule timing depends on the ESP32 clock and its hardcoded Eastern timezone setting, not on the frontend timezone dropdown.

---

## Quick Backend Smoke Tests (curl)

```bash
# Health check
curl http://127.0.0.1:8000/health

# Login
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"wei.wei@uconn.edu","password":"password123"}'

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

### Frontend to Backend to ESP32

1. Start the simulator, backend, and frontend (see Run the Project above).
2. Open the app and log in with `wei.wei@uconn.edu` / `password123`.
3. On Dashboard, tap the bulb to toggle lights.
4. Watch the backend logs for `MQTT bridge: published 'on'`.
5. Watch the simulator for `Received cmd <- 'on'` and `LOAD=ON`.
6. Toggle again and confirm `off` / `LOAD=OFF`.
7. Open History and verify events appear.

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
sqlite3 backend/app/database/lights.db \
  "SELECT * FROM restaurant_lights; \
   SELECT '---'; \
   SELECT email, name, restaurant_id FROM users; \
   SELECT '---'; \
   SELECT * FROM light_history ORDER BY timestamp DESC LIMIT 5; \
   SELECT '---'; \
   SELECT * FROM weekly_schedule;"
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
source venv/bin/activate && python main.py

# run-frontend
cd frontend && npx expo start -c
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
