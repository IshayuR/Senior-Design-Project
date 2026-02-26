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
