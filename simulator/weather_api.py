from flask import Flask, jsonify, request
import random, time
from datetime import datetime

app = Flask(__name__)

API_KEY = "lab31-secret-key"
start_time = time.time()

state = {
    "temperature": 22.0,
    "humidity": 55.0,
    "pressure": 1013.0,
    "wind_speed": 3.5,
}

@app.before_request
def auth():
    if request.headers.get("X-API-Key") != API_KEY:
        return jsonify({"error": "unauthorized"}), 401

@app.route("/api/weather/current")
def current():
    state["temperature"] += random.uniform(-0.3, 0.3)
    state["humidity"] += random.uniform(-0.5, 0.5)
    state["pressure"] += random.uniform(-0.2, 0.2)
    state["wind_speed"] = max(0.0, state["wind_speed"] + random.uniform(-0.4, 0.4))
    return jsonify({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "temperature": round(state["temperature"], 1),
        "humidity": round(state["humidity"], 1),
        "pressure": round(state["pressure"], 1),
        "wind_speed": round(state["wind_speed"], 1),
    })

@app.route("/api/weather/status")
def status():
    return jsonify({
        "status": "online",
        "uptime_seconds": int(time.time() - start_time),
        "version": "1.0.0",
    })

@app.route("/api/weather/devices")
def devices():
    total = 5
    online = total - random.choice([0, 0, 1])
    return jsonify({
        "total": total,
        "online": online,
        "offline": total - online,
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
