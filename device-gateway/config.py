"""MQTT / AWS IoT config from environment."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

ROOT = Path(__file__).resolve().parent

AWS_IOT_ENDPOINT = os.getenv("AWS_IOT_ENDPOINT", "")
PORT = int(os.getenv("MQTT_PORT", "8883"))
CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "esp32")
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "restaurants/proof-of-concept/control")

CA_CERT = os.getenv("CA_CERT") or str(ROOT / "AmazonRootCA1.pem")
CERTFILE = os.getenv("CERTFILE") or str(ROOT / "certificate.pem.crt")
KEYFILE = os.getenv("KEYFILE") or str(ROOT / "private.pem.key")

# Backend API for schedule (cron job fetches schedule and applies at schedule_on/schedule_off)
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
RESTAURANT_ID = int(os.getenv("RESTAURANT_ID", "1"))
# Cron: run schedule check every minute
SCHEDULER_CRON_MINUTE = os.getenv("SCHEDULER_CRON_MINUTE", "*")
SCHEDULER_CRON_HOUR = os.getenv("SCHEDULER_CRON_HOUR", "*")

# Local MQTT (no AWS, no certs): set LOCAL_MQTT=1 and run a broker on localhost (e.g. Mosquitto)
LOCAL_MQTT = os.getenv("LOCAL_MQTT", "").lower() in ("1", "true", "yes")
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_LOCAL_PORT = int(os.getenv("MQTT_LOCAL_PORT", "1883"))
