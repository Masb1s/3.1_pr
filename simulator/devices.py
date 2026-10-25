import time
import random
import json
import paho.mqtt.client as mqtt
import argparse
import os
import uuid

# Шлях до сертифікату відносно папки, де лежить скрипт
CA_CERT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "certs", "ca.crt")
BROKER = "localhost"
PORT = 8883

class SmartHomeSimulator:
    def __init__(self):
        # Унікальний ID для кожного запуску
        unique_id = f"sim_{uuid.uuid4().hex[:6]}"
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=unique_id)
        self.client.tls_set(ca_certs=CA_CERT)
        self.client.username_pw_set("admin", "SuperSecretAdminPass")
        
        # Last Will
        self.client.will_set("home/main/simulator/status", payload="offline", qos=1, retain=True)
        
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(BROKER, PORT, 60)
        self.client.loop_start()

        self.state = {
            "living_motion": False,
            "living_lux": 300,
            "temperature": 21.0,
            "humidity": 45.0,
            "power": 500,
            "living_light": {"state": "OFF", "brightness": 0},
            "heater": {"state": "ON", "setpoint": 21.0}
        }

    def on_connect(self, client, userdata, flags, rc):
        print(f"✅ Підключено до MQTT (TLS) з кодом {rc}")
        self.client.publish("home/main/simulator/status", "online", qos=1, retain=True)
        
        # Відправляємо початковий стан пристроїв, щоб OpenHAB їх одразу побачив
        self.publish_state("living_room", "light", self.state["living_light"])
        self.publish_state("living_room", "heater", self.state["heater"])
        
        client.subscribe("home/+/+/set")

    def on_message(self, client, userdata, msg):
        topic = msg.topic.split('/')
        zone, device = topic[1], topic[2]
        payload = json.loads(msg.payload.decode())
        
        if device == "light":
            # Якщо надійшла команда вимкнути/увімкнути
            if "state" in payload:
                self.state["living_light"]["state"] = payload["state"]
                if payload["state"] == "OFF":
                    self.state["living_light"]["brightness"] = 0
                elif payload["state"] == "ON" and self.state["living_light"]["brightness"] == 0:
                    self.state["living_light"]["brightness"] = 100

            # Якщо надійшла команда змінити яскравість
            if "brightness" in payload:
                self.state["living_light"]["brightness"] = int(payload["brightness"])
                if int(payload["brightness"]) > 0:
                    self.state["living_light"]["state"] = "ON"
                else:
                    self.state["living_light"]["state"] = "OFF"
                    
            self.publish_state("living_room", "light", self.state["living_light"])

        elif device == "heater":
            if "state" in payload:
                self.state["heater"]["state"] = payload["state"]
            if "setpoint" in payload:
                self.state["heater"]["setpoint"] = payload["setpoint"]
            self.publish_state("living_room", "heater", self.state["heater"])

    def publish_telemetry(self, zone, device, value, unit):
        if isinstance(value, (int, float)):
            val = round(value, 1)
        else:
            val = value
        payload = {"value": val, "unit": unit, "ts": int(time.time())}
        self.client.publish(f"home/{zone}/{device}/telemetry", json.dumps(payload), qos=1)

    def publish_state(self, zone, device, state_dict):
        self.client.publish(f"home/{zone}/{device}/state", json.dumps(state_dict), qos=1)

    def run_scenario(self, scenario):
        print(f"🎬 Запуск сценарію: {scenario}")
        if scenario == "motion":
            self.state["living_motion"] = True
            self.state["living_lux"] = 20
            self.publish_telemetry("living_room", "motion", "ON", "string") 
            self.publish_telemetry("living_room", "lux", 20, "lx")
            time.sleep(5)
            self.state["living_motion"] = False
            self.publish_telemetry("living_room", "motion", "OFF", "string")
            
        elif scenario == "overload":
            self.state["power"] = 2800
            self.publish_telemetry("main", "power", 2800, "W")
            
        elif scenario == "nobody_home":
            self.state["living_motion"] = False
            self.publish_telemetry("living_room", "motion", "OFF", "string")

    def run(self):
        try:
            while True:
                self.state["temperature"] += random.uniform(-0.1, 0.1)
                self.state["living_lux"] = max(0, self.state["living_lux"] + random.randint(-10, 10))
                self.state["power"] = random.randint(300, 1500)
                
                self.publish_telemetry("main", "climate", self.state["temperature"], "C")
                self.publish_telemetry("living_room", "lux", self.state["living_lux"], "lx")
                self.publish_telemetry("main", "power", self.state["power"], "W")
                
                time.sleep(2)
        except KeyboardInterrupt:
            print("🛑 Завершення...")
            self.client.publish("home/main/simulator/status", "offline", qos=1, retain=True)
            self.client.loop_stop()
            self.client.disconnect()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=str, default=None)
    args = parser.parse_args()

    sim = SmartHomeSimulator()
    if args.scenario:
        sim.run_scenario(args.scenario)
        time.sleep(2)
    else:
        sim.run()