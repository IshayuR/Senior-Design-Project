"""AWS IoT MQTT client: connect once, publish light state on demand."""
import json
import ssl

import paho.mqtt.client as mqtt  # type: ignore[reportMissingImports]

from config import (
    AWS_IOT_ENDPOINT,
    CA_CERT,
    CERTFILE,
    CLIENT_ID,
    KEYFILE,
    MQTT_TOPIC,
    PORT,
)

_client: mqtt.Client | None = None


def _get_client() -> mqtt.Client:
    global _client
    if _client is None:
        if not AWS_IOT_ENDPOINT:
            raise RuntimeError("AWS_IOT_ENDPOINT not set; cannot connect to MQTT")
        _client = mqtt.Client(client_id=CLIENT_ID)
        _client.tls_set(
            ca_certs=CA_CERT,
            certfile=CERTFILE,
            keyfile=KEYFILE,
            tls_version=ssl.PROTOCOL_TLSv1_2,
        )
        _client.connect(AWS_IOT_ENDPOINT, PORT)
    return _client


def publish_light_state(state: str) -> None:
    """Publish state ('on' or 'off') to the configured MQTT topic."""
    payload = json.dumps({"state": state})
    _get_client().publish(MQTT_TOPIC, payload)


def disconnect() -> None:
    """Disconnect the MQTT client (e.g. on shutdown)."""
    global _client
    if _client:
        _client.disconnect()
        _client = None
