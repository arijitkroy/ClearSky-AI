import time
import random
import datetime
import requests
import math
from typing import List, Dict, Any

import os

# Target API endpoint
INGEST_URL = os.getenv("INGEST_URL")
if not INGEST_URL:
    port = os.getenv("PORT", "8000")
    INGEST_URL = f"http://127.0.0.1:{port}/api/v1/sensors/ingest-batch"


# Neighborhood configurations around a New Delhi centroid (Lat: 28.6139, Lon: 77.2090)
NEIGHBORHOODS = {
    "Industrial Zone": {
        "center": (28.6500, 77.1200),
        "radius": 0.02,
        "base_pollutants": {"pm25": 140, "pm10": 220, "co": 1.8, "no2": 75, "so2": 45, "o3": 35},
        "variance": 15
    },
    "Downtown Business District": {
        "center": (28.6300, 77.2200),
        "radius": 0.015,
        "base_pollutants": {"pm25": 85, "pm10": 130, "co": 2.5, "no2": 60, "so2": 15, "o3": 40},
        "variance": 10
    },
    "Residential East": {
        "center": (28.6200, 77.2800),
        "radius": 0.02,
        "base_pollutants": {"pm25": 55, "pm10": 85, "co": 0.8, "no2": 30, "so2": 10, "o3": 45},
        "variance": 8
    },
    "Green Valley Park": {
        "center": (28.5800, 77.2100),
        "radius": 0.01,
        "base_pollutants": {"pm25": 25, "pm10": 45, "co": 0.4, "no2": 15, "so2": 5, "o3": 55},
        "variance": 5
    },
    "Construction Site North": {
        "center": (28.6900, 77.1800),
        "radius": 0.015,
        "base_pollutants": {"pm25": 110, "pm10": 290, "co": 1.2, "no2": 45, "so2": 12, "o3": 30},
        "variance": 20
    },
    "Suburbs West": {
        "center": (28.6100, 77.0800),
        "radius": 0.025,
        "base_pollutants": {"pm25": 48, "pm10": 75, "co": 0.7, "no2": 25, "so2": 8, "o3": 42},
        "variance": 6
    }
}

class AirQualitySimulator:
    def __init__(self, num_sensors: int = 100):
        self.num_sensors = num_sensors
        self.sensors: List[Dict[str, Any]] = []
        self.current_event = "normal"  # normal, rain, rush_hour, construction, failure
        self.event_intensity = 1.0
        self.drifts: Dict[str, Dict[str, float]] = {}  # sensor_id -> pollutant -> drift_val
        self.step_count = 0
        
        self._initialize_sensors()

    def _initialize_sensors(self):
        """Creates metadata for approximately 100 sensors spread across neighborhoods."""
        sensors_per_neighborhood = math.ceil(self.num_sensors / len(NEIGHBORHOODS))
        sensor_index = 1
        
        for name, config in NEIGHBORHOODS.items():
            for _ in range(sensors_per_neighborhood):
                if sensor_index > self.num_sensors:
                    break
                    
                sensor_id = f"SEN-{sensor_index:03d}"
                
                # Generate random lat/lon within neighborhood radius using box-muller
                angle = random.uniform(0, 2 * math.pi)
                dist = random.uniform(0, config["radius"])
                lat = config["center"][0] + dist * math.sin(angle)
                lon = config["center"][1] + dist * math.cos(angle)
                
                self.sensors.append({
                    "id": sensor_id,
                    "name": f"{name} Sensor {sensor_index}",
                    "latitude": round(lat, 5),
                    "longitude": round(lon, 5),
                    "neighbourhood": name,
                    "status": "active",
                    "battery_level": round(random.uniform(85.0, 100.0), 1),
                    "fail_timer": 0
                })
                
                # Setup random walk drift trackers for this sensor
                self.drifts[sensor_id] = {
                    "pm25": 0.0, "pm10": 0.0, "co": 0.0, "no2": 0.0, "so2": 0.0, "o3": 0.0
                }
                
                sensor_index += 1

    def set_event(self, event_type: str, intensity: float = 1.0):
        """Triggers simulation weather/event controls."""
        self.current_event = event_type
        self.event_intensity = intensity

    def _generate_sensor_readings(self) -> List[Dict[str, Any]]:
        """Generates realistic sensor data based on time, neighborhood and weather events."""
        self.step_count += 1
        now = datetime.datetime.now()
        hour = now.hour
        day_of_week = now.weekday()
        
        # Diurnal Factors (Rush hour traffic peaks)
        # Peak 1: 8-10 AM (Morning rush)
        # Peak 2: 5-8 PM (Evening rush)
        traffic_factor = 1.0
        if 8 <= hour <= 10:
            traffic_factor = 1.6 + 0.2 * math.sin((hour - 8) * math.pi / 2)
        elif 17 <= hour <= 20:
            traffic_factor = 1.8 + 0.2 * math.sin((hour - 17) * math.pi / 3)
        else:
            # Late night dip
            if 0 <= hour <= 5:
                traffic_factor = 0.5
            else:
                traffic_factor = 0.8
                
        # Weekend traffic reduction (30% less traffic on Sat/Sun)
        if day_of_week >= 5:
            traffic_factor *= 0.7
            
        # Weather parameters for the city
        # Standard wind / humidity base
        city_wind_speed = 3.5 + 1.5 * math.sin(hour * math.pi / 12) + random.uniform(-0.5, 0.5)
        city_humidity = 55.0 + 20.0 * math.cos(hour * math.pi / 12) + random.uniform(-5, 5)
        city_temp = 28.0 - 6.0 * math.cos((hour - 4) * math.pi / 12) + random.uniform(-1, 1)
        city_pressure = 1010.0 + random.uniform(-2, 2)
        city_wind_dir = (180 + 45 * math.sin(hour * math.pi / 24)) % 360  # Mostly Southerly/North-Westerly

        # Modify weather parameters based on events
        rain_factor = 1.0
        wind_factor = 1.0
        construction_multiplier = 1.0
        traffic_multiplier = 1.0
        
        if self.current_event == "rain":
            # Rain washes out PM, increases humidity, drops temperature
            city_humidity = min(98.0, 85.0 + 15.0 * self.event_intensity)
            city_temp -= 4.0 * self.event_intensity
            rain_factor = 0.25  # 75% washout of PM
            city_wind_speed += 2.0 * self.event_intensity
            
        elif self.current_event == "rush_hour":
            # Heavy traffic spike (spikes CO and NO2 by 2.2x)
            traffic_multiplier = 2.2 * self.event_intensity
            
        elif self.current_event == "construction":
            # Construction storm (spikes PM10 by 3.5x)
            construction_multiplier = 3.5 * self.event_intensity
            
        # If wind is high, disperse pollutants
        if city_wind_speed > 6.0:
            wind_factor = 0.65  # 35% dispersion reduction
        elif city_wind_speed < 1.5:
            wind_factor = 1.35  # Pollutants accumulate in stagnant air

        readings_batch = []
        
        for s in self.sensors:
            sensor_id = s["id"]
            nb = s["neighbourhood"]
            cfg = NEIGHBORHOODS[nb]
            
            # Handle fail timers / offline state
            if s["status"] == "offline":
                s["fail_timer"] -= 1
                if s["fail_timer"] <= 0:
                    s["status"] = "active"
                    s["battery_level"] = round(random.uniform(40, 80), 1)
                continue
                
            # Random device failure logic
            # 0.1% chance of temporary sensor failure (offline for 6-12 cycles)
            if self.current_event == "failure" or random.random() < 0.001:
                s["status"] = "offline"
                s["fail_timer"] = random.randint(6, 12)
                continue
                
            # Battery discharge
            s["battery_level"] = max(0.0, round(s["battery_level"] - 0.03, 2))
            if s["battery_level"] <= 5.0:
                s["status"] = "offline"
                s["fail_timer"] = 30  # Battery dead for a long time (till recharge simulation)
                continue
                
            # Apply random walk drift to pollutants
            for p in self.drifts[sensor_id]:
                self.drifts[sensor_id][p] += random.uniform(-0.15, 0.15)
                # Cap drift to avoid unrealistic values
                self.drifts[sensor_id][p] = max(-10.0, min(10.0, self.drifts[sensor_id][p]))
                
            drift = self.drifts[sensor_id]
            
            # Base generation values
            pm25_val = cfg["base_pollutants"]["pm25"]
            pm10_val = cfg["base_pollutants"]["pm10"]
            co_val = cfg["base_pollutants"]["co"]
            no2_val = cfg["base_pollutants"]["no2"]
            so2_val = cfg["base_pollutants"]["so2"]
            o3_val = cfg["base_pollutants"]["o3"]
            
            # Apply simulation dynamics
            # 1. PM2.5 and PM10 are highly traffic and weather dependent
            pm25 = (pm25_val * traffic_factor * rain_factor * wind_factor) + drift["pm25"]
            pm10 = (pm10_val * traffic_factor * rain_factor * wind_factor) + drift["pm10"]
            
            # Adjust if specific events occur
            if nb == "Construction Site North":
                pm10 *= construction_multiplier
                pm25 *= (1.0 + (construction_multiplier - 1.0) * 0.4)
            elif nb == "Downtown Business District":
                co_val *= traffic_multiplier
                no2_val *= traffic_multiplier
                pm25 *= (1.0 + (traffic_multiplier - 1.0) * 0.3)
            elif nb == "Industrial Zone":
                so2_val *= (1.0 + random.uniform(-0.1, 0.2))
                no2_val *= (1.0 + random.uniform(-0.1, 0.1))
                
            co = (co_val * traffic_factor * wind_factor) + drift["co"]
            no2 = (no2_val * traffic_factor * wind_factor) + drift["no2"]
            so2 = (so2_val * wind_factor) + drift["so2"]
            o3 = (o3_val * (city_temp / 28.0) * (1.0 - city_humidity / 150.0)) + drift["o3"]
            
            # Add stochastic variance
            var = cfg["variance"]
            pm25 = max(2.0, pm25 + random.uniform(-var, var))
            pm10 = max(5.0, pm10 + random.uniform(-var * 2.0, var * 2.0))
            co = max(0.05, co + random.uniform(-0.1, 0.1))
            no2 = max(2.0, no2 + random.uniform(-var * 0.3, var * 0.3))
            so2 = max(1.0, so2 + random.uniform(-var * 0.1, var * 0.1))
            o3 = max(1.0, o3 + random.uniform(-var * 0.2, var * 0.2))
            
            # Microclimate sensor variations
            s_temp = city_temp + random.uniform(-0.8, 0.8)
            s_hum = min(100.0, max(5.0, city_humidity + random.uniform(-3, 3)))
            s_wind_sp = max(0.0, city_wind_speed + random.uniform(-0.5, 0.5))
            s_wind_dir = (city_wind_dir + random.uniform(-15, 15)) % 360
            
            # 5% chance of returning a missing value for a pollutant (simulating sensor packet drops)
            readings_dict = {
                "sensor_id": sensor_id,
                "timestamp": now.isoformat(),
                "pm25": round(pm25, 1) if random.random() > 0.03 else None,
                "pm10": round(pm10, 1) if random.random() > 0.03 else None,
                "co": round(co, 2) if random.random() > 0.03 else None,
                "no2": round(no2, 1) if random.random() > 0.03 else None,
                "so2": round(so2, 1) if random.random() > 0.03 else None,
                "o3": round(o3, 1) if random.random() > 0.03 else None,
                "temperature": round(s_temp, 1),
                "humidity": round(s_hum, 1),
                "pressure": round(city_pressure, 1),
                "wind_speed": round(s_wind_sp, 1),
                "wind_direction": int(s_wind_dir),
                "battery_level": s["battery_level"]
            }
            
            readings_batch.append(readings_dict)
            
        return readings_batch

    def run_cycle(self) -> bool:
        """Runs a single simulation cycle, generating readings and POSTing them to the API."""
        try:
            # Generate readings
            payload = self._generate_sensor_readings()
            
            # Also send the metadata registration block if this is the first few cycles
            # to make sure sensors are in the database
            sensors_meta = [
                {
                    "id": s["id"],
                    "name": s["name"],
                    "latitude": s["latitude"],
                    "longitude": s["longitude"],
                    "neighbourhood": s["neighbourhood"],
                    "status": s["status"],
                    "battery_level": s["battery_level"]
                }
                for s in self.sensors
            ]
            
            # Post data to backend
            full_payload = {
                "sensors": sensors_meta,
                "readings": payload
            }
            
            response = requests.post(INGEST_URL, json=full_payload, timeout=2.0)
            if response.status_code == 200:
                print(f"Cycle {self.step_count} completed. Ingested {len(payload)} sensor readings successfully.")
                return True
            else:
                print(f"Failed to ingest readings (HTTP {response.status_code}): {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"Connection to backend failed, waiting... (Error: {e})")
            return False

def run_simulator_loop():
    """Starts the standalone simulator loop."""
    print("ClearSky AI IoT Sensor Simulator Starting...")
    simulator = AirQualitySimulator()
    
    # Check if there is an active event control file or endpoint
    # Run in a loop
    while True:
        # Check simulator state updates from a local temporary state or just standard loop
        # We can implement a simple control file in the workspace
        control_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "simulator_control.json")
        import json
        if os.path.exists(control_file):
            try:
                with open(control_file, "r") as f:
                    data = json.load(f)
                    event_type = data.get("event_type", "normal")
                    intensity = data.get("intensity", 1.0)
                    simulator.set_event(event_type, intensity)
            except Exception:
                pass
                
        simulator.run_cycle()
        time.sleep(5)

if __name__ == "__main__":
    run_simulator_loop()
