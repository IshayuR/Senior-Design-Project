# Cloud-Connected Restaurant Lighting Backend (CSE Senior Design, Budderfly)

This project implements the backend system for an IoT-enabled restaurant lighting control solution, as part of a joint ECE/CSE senior design project with Budderfly. The focus is on demonstrating cloud integration, remote state management, and scalable backend software architecture for responsive lighting control.

## Overview

The backend provides API endpoints, MQTT integration, and state management for simulated restaurant lighting across multiple locations. Users interact through a web-based UI, with commands routed to the cloud and handled in real time.

## Project Goals

- Establish secure one-way MQTT connection between Python backend and AWS IoT Core
- Enable the backend to publish control commands to cloud-based devices (ESP32s)
- Simulate and store lighting states for multiple restaurant zones in a mock database
- Provide a robust codebase for rapid prototyping, future expansion, and team collaboration

## Technologies

- **AWS IoT Core** (MQTT Broker for device communication)
- **Python (Flask / FastAPI)** for backend REST API and MQTT publishing
- **paho-mqtt** for Python-based MQTT connectivity
- **SQLite or PostgreSQL** (mock database for lighting state)
- **Git** for code management and collaboration

## Key Files

- `main.py` – Entry point; runs the Flask app (`python main.py`)
- `app.py` – Flask app: `POST /light` receives state, publishes to MQTT, returns JSON
- `mqtt_client.py` – MQTT client (connect once, `publish_light_state(state)`)
- `config.py` – Loads AWS/MQTT settings from `.env`
- `.env.example` – Template for `AWS_IOT_ENDPOINT`, cert paths, topic (copy to `.env`)
- `requirements.txt` – Flask, paho-mqtt, python-dotenv
- `.gitignore` – Excludes `.env`, `*.pem`, `*.crt`, `*.key`

## Security

- **Certificates/keys are never committed**; always handled via `.gitignore`
- Environment variables (`.env`) recommended for AWS credentials and configuration

## Setup Instructions

1. Clone this repository and `cd device-gateway`.
2. Install dependencies: `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and set `AWS_IOT_ENDPOINT` (and cert paths if needed).  
   Without `.env`, `POST /light` still works but MQTT publish is skipped.
4. Put AWS IoT certs in this folder (or set `CA_CERT`, `CERTFILE`, `KEYFILE` in `.env`). Never commit certs.
5. Run: `python main.py`. Service listens on `http://0.0.0.0:5000`.  
   Test: `curl -X POST http://localhost:5000/light -H "Content-Type: application/json" -d "{\"state\":\"on\"}"`.

## References

See `Works Cited` in the project report for architecture, MQTT, and IoT resource documentation.

---

Designed and maintained by the CSE team, University of Connecticut. Project sponsored by Budderfly.
