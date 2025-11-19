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

- `main.py`: Main backend service
- `.gitignore`: Excludes sensitive files and local environments (see below)
- `requirements.txt`: Python dependencies (e.g., paho-mqtt, Flask)
- `README.md`: Project documentation

## Security

- **Certificates/keys are never committed**; always handled via `.gitignore`
- Environment variables (`.env`) recommended for AWS credentials and configuration

## Setup Instructions

1. Clone this repository.
2. Create a Python virtual environment (`python3 -m venv venv`).
3. Install dependencies from `requirements.txt`.
4. Ensure the following files are present (but NOT tracked by Git):
    - AWS IoT certificate, private key, and CA (see `.gitignore`).
5. Configure connection parameters in `main.py` or via environment variables.
6. Launch backend service and test cloud connection (see usage in code comments).

## References

See `Works Cited` in the project report for architecture, MQTT, and IoT resource documentation.

---

Designed and maintained by the CSE team, University of Connecticut. Project sponsored by Budderfly.
