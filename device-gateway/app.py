"""Flask app: POST /light receives state and publishes to MQTT; cron scheduler applies light schedule."""
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/light", methods=["POST"])
def control_light():
    data = request.json or {}
    state = data.get("state", "off")

    print("Received light state:", state)

    try:
        from mqtt_client import publish_light_state
        publish_light_state(state)
    except Exception as e:
        print("MQTT publish failed:", e)

    return jsonify({"status": "ok", "received": state})


def run(host: str = "0.0.0.0", port: int = 5000) -> None:
    import os
    if os.getenv("DISABLE_SCHEDULER", "").lower() not in ("1", "true", "yes"):
        from scheduler import start_scheduler
        start_scheduler()
    app.run(host=host, port=port)
