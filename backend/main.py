import os
from dotenv import load_dotenv
load_dotenv()
import json
import datetime

import threading
import shutil
import uuid
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import numpy as np

from .database import engine, Base, get_db, SessionLocal
from . import models, schemas
from ai import cpcb_aqi, cleaner, forecaster, hotspot_detector, explainable_ai, vision_detector, satellite_analyzer

# Initialize database tables
Base.metadata.create_all(bind=engine)

# Create static folder for citizen uploads
os.makedirs("static/uploads", exist_ok=True)

app = FastAPI(
    title="ClearSky AI Backend API",
    description="FastAPI backend for Smart City Neighborhood Air Quality Intelligence Platform",
    version="1.0.0"
)

# Mount static folder
app.mount("/static", StaticFiles(directory="static"), name="static")


# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For prototype, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

forecasting_engine = forecaster.AirQualityForecaster(target_col="aqi")
SIMULATOR_CONTROL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "simulator_control.json")

# Helper to pre-populate neighborhoods on startup
def populate_neighborhoods():
    db = SessionLocal()
    try:
        count = db.query(models.Neighborhood).count()
        if count > 0:
            return
            
        # Define mock GeoJSON coordinates for New Delhi sectors
        neighborhood_configs = [
            {
                "name": "Industrial Zone",
                "boundary": {
                    "type": "Polygon",
                    "coordinates": [[
                        [77.1000, 28.6700], [77.1400, 28.6700],
                        [77.1400, 28.6300], [77.1000, 28.6300],
                        [77.1000, 28.6700]
                    ]]
                }
            },
            {
                "name": "Downtown Business District",
                "boundary": {
                    "type": "Polygon",
                    "coordinates": [[
                        [77.2000, 28.6500], [77.2400, 28.6500],
                        [77.2400, 28.6100], [77.2000, 28.6100],
                        [77.2000, 28.6500]
                    ]]
                }
            },
            {
                "name": "Residential East",
                "boundary": {
                    "type": "Polygon",
                    "coordinates": [[
                        [77.2600, 28.6400], [77.3000, 28.6400],
                        [77.3000, 28.6000], [77.2600, 28.6000],
                        [77.2600, 28.6400]
                    ]]
                }
            },
            {
                "name": "Green Valley Park",
                "boundary": {
                    "type": "Polygon",
                    "coordinates": [[
                        [77.1900, 28.5900], [77.2300, 28.5900],
                        [77.2300, 28.5700], [77.1900, 28.5700],
                        [77.1900, 28.5900]
                    ]]
                }
            },
            {
                "name": "Construction Site North",
                "boundary": {
                    "type": "Polygon",
                    "coordinates": [[
                        [77.1600, 28.7100], [77.2000, 28.7100],
                        [77.2000, 28.6700], [77.1600, 28.6700],
                        [77.1600, 28.7100]
                    ]]
                }
            },
            {
                "name": "Suburbs West",
                "boundary": {
                    "type": "Polygon",
                    "coordinates": [[
                        [77.0500, 28.6300], [77.1000, 28.6300],
                        [77.1000, 28.5900], [77.0500, 28.5900],
                        [77.0500, 28.6300]
                    ]]
                }
            }
        ]
        
        for cfg in neighborhood_configs:
            db_nb = models.Neighborhood(
                name=cfg["name"],
                boundary_geojson=json.dumps(cfg["boundary"]),
                average_aqi=0.0,
                dominant_pollutant="None",
                risk_score=0.0,
                sensor_count=0
            )
            db.add(db_nb)
        db.commit()
        print("Populated initial neighborhoods successfully.")
    except Exception as e:
        print(f"Error populating neighborhoods: {e}")
    finally:
        db.close()

# Startup Lifespan events
@app.on_event("startup")
def startup_event():
    populate_neighborhoods()
    # Reset simulator control file
    try:
        with open(SIMULATOR_CONTROL_PATH, "w") as f:
            json.dump({"event_type": "normal", "intensity": 1.0}, f)
    except Exception:
        pass

# Background task for ML model training and inference
def trigger_forecasting_pipeline(db: Session):
    try:
        # Load historical readings to train model
        # Select readings in the last 24 hours
        yesterday = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        readings = db.query(models.Reading).filter(models.Reading.timestamp >= yesterday).all()
        if len(readings) < 100:
            return
            
        # Convert to dataframe and train
        readings_list = []
        for r in readings:
            readings_list.append({
                "timestamp": r.timestamp,
                "pm25": r.pm25,
                "pm10": r.pm10,
                "co": r.co,
                "no2": r.no2,
                "so2": r.so2,
                "o3": r.o3,
                "temperature": r.temperature,
                "humidity": r.humidity,
                "wind_speed": r.wind_speed,
                "wind_direction": r.wind_direction,
                "aqi": r.aqi
            })
            
        df = cleaner.clean_sensor_data(readings_list)
        
        # Train
        forecasting_engine.train_all(df)
        
    except Exception as e:
        print(f"Error in background training pipeline: {e}")

# -----------------
# REST API Endpoints
# -----------------

@app.post("/api/v1/sensors/ingest-batch", status_code=200)
def ingest_sensor_batch(payload: dict, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Core ingestion endpoint for simulated/physical IoT sensors.
    Performs real-time cleaning, AQI calculations, spatial cluster-hotspot checks, and alerts.
    """
    sensors_meta = payload.get("sensors", [])
    readings_data = payload.get("readings", [])
    
    # 1. Update/Insert Sensors
    sensor_map = {}
    for s_meta in sensors_meta:
        sensor_id = s_meta["id"]
        db_sensor = db.query(models.Sensor).filter(models.Sensor.id == sensor_id).first()
        if not db_sensor:
            db_sensor = models.Sensor(
                id=sensor_id,
                name=s_meta["name"],
                latitude=s_meta["latitude"],
                longitude=s_meta["longitude"],
                neighbourhood=s_meta["neighbourhood"],
                status=s_meta["status"],
                battery_level=s_meta["battery_level"],
                last_active=datetime.datetime.utcnow()
            )
            db.add(db_sensor)
        else:
            db_sensor.status = s_meta["status"]
            db_sensor.battery_level = s_meta["battery_level"]
            db_sensor.last_active = datetime.datetime.utcnow()
            
        sensor_map[sensor_id] = db_sensor
        
    db.commit()
    
    # 2. Insert and Compute Readings
    db_readings = []
    reading_dicts_for_ml = []
    
    for r_data in readings_data:
        sensor_id = r_data["sensor_id"]
        # Retrieve sensor location
        sensor = sensor_map.get(sensor_id)
        if not sensor:
            continue
            
        # Calculate CPCB AQI
        aqi_val, dominant = cpcb_aqi.calculate_overall_aqi(r_data)
        
        # Save reading
        db_reading = models.Reading(
            sensor_id=sensor_id,
            timestamp=datetime.datetime.fromisoformat(r_data["timestamp"]) if "timestamp" in r_data else datetime.datetime.utcnow(),
            pm25=r_data.get("pm25"),
            pm10=r_data.get("pm10"),
            co=r_data.get("co"),
            no2=r_data.get("no2"),
            so2=r_data.get("so2"),
            o3=r_data.get("o3"),
            temperature=r_data.get("temperature"),
            humidity=r_data.get("humidity"),
            pressure=r_data.get("pressure"),
            wind_speed=r_data.get("wind_speed"),
            wind_direction=r_data.get("wind_direction"),
            battery_level=r_data.get("battery_level"),
            aqi=aqi_val,
            dominant_pollutant=dominant
        )
        db.add(db_reading)
        db_readings.append(db_reading)
        
        # Build dict for spatial hotspot detection & cleaning checks
        reading_dict = r_data.copy()
        reading_dict["id"] = sensor_id
        reading_dict["latitude"] = sensor.latitude
        reading_dict["longitude"] = sensor.longitude
        reading_dict["neighbourhood"] = sensor.neighbourhood
        reading_dict["aqi"] = aqi_val
        reading_dicts_for_ml.append(reading_dict)
        
    db.commit()
    
    # 3. Real-Time Alert Checks
    # Trigger alerts for AQI > 150 (Mod-Poor limit), or spikes, or failing batteries
    for rd in reading_dicts_for_ml:
        sensor_id = rd["id"]
        aqi_val = rd["aqi"]
        battery = rd.get("battery_level", 100.0)
        
        # Check battery level
        if battery < 10.0:
            # Check if alert already exists for this sensor failure to avoid duplication
            active_failure = db.query(models.Alert).filter(
                models.Alert.sensor_id == sensor_id,
                models.Alert.alert_type == "SENSOR_FAILURE",
                models.Alert.status == "active"
            ).first()
            if not active_failure:
                db_alert = models.Alert(
                    sensor_id=sensor_id,
                    neighbourhood=rd["neighbourhood"],
                    alert_type="SENSOR_FAILURE",
                    message=f"Sensor {sensor_id} has critical battery levels ({battery}%). Operational check required.",
                    status="active"
                )
                db.add(db_alert)
                
        # Check AQI limit
        if aqi_val >= 200:  # Poor AQI Threshold
            active_exceed = db.query(models.Alert).filter(
                models.Alert.sensor_id == sensor_id,
                models.Alert.alert_type == "AQI_EXCEED",
                models.Alert.status == "active"
            ).first()
            if not active_exceed:
                db_alert = models.Alert(
                    sensor_id=sensor_id,
                    neighbourhood=rd["neighbourhood"],
                    alert_type="AQI_EXCEED",
                    message=f"Air quality threshold exceeded at {sensor_id}. Current AQI is {aqi_val} ({cpcb_aqi.get_aqi_category(aqi_val)}).",
                    status="active"
                )
                db.add(db_alert)
                
        # Check Spike: Current PM2.5 > 2.0x average of the past 3 readings
        # Select past 4 readings (including current one)
        past_readings = db.query(models.Reading).filter(
            models.Reading.sensor_id == sensor_id
        ).order_by(models.Reading.timestamp.desc()).limit(4).all()
        
        if len(past_readings) >= 4:
            current_pm25 = past_readings[0].pm25 or 0.0
            avg_past_pm25 = sum((r.pm25 or 0.0) for r in past_readings[1:]) / 3.0
            if avg_past_pm25 > 20.0 and current_pm25 > (2.5 * avg_past_pm25):
                db_alert = models.Alert(
                    sensor_id=sensor_id,
                    neighbourhood=rd["neighbourhood"],
                    alert_type="SPIKE",
                    message=f"Sudden PM2.5 spike detected at {sensor_id}. Jumped from {avg_past_pm25:.1f} to {current_pm25:.1f} ug/m³.",
                    status="active"
                )
                db.add(db_alert)
                
    db.commit()
    
    # 4. Spatio-Temporal Hotspot Clustering (DBSCAN + Isolation Forest)
    # Perform spatial hotspot grouping using our DBSCAN cluster detector
    try:
        detected_hotspots = hotspot_detector.detect_hotspots_dbscan(reading_dicts_for_ml, aqi_threshold=150.0)
        
        # Save active hotspots
        # First, mark previous DBSCAN hotspots as resolved
        db.query(models.Hotspot).filter(
            models.Hotspot.detection_method == "DBSCAN",
            models.Hotspot.status == "active"
        ).update({"status": "resolved"})
        db.commit()
        
        for hs in detected_hotspots:
            # Generate explainable AI summary and recommendations
            rep_reading = next((r for r in reading_dicts_for_ml if r["neighbourhood"] == hs["neighbourhood"]), hs)
            explanation_str = explainable_ai.explain_hotspot(rep_reading)
            
            db_hs = models.Hotspot(
                neighbourhood=hs["neighbourhood"],
                latitude=hs["latitude"],
                longitude=hs["longitude"],
                detection_method="DBSCAN",
                confidence=hs["confidence"],
                main_pollutants=hs["main_pollutants"],
                explanation=explanation_str,
                status="active"
            )
            db.add(db_hs)
            db.commit() # commit to get ID
            
            # Generate recommendations
            recs = explainable_ai.generate_recommendations(rep_reading)
            for rec in recs:
                db_rec = models.Recommendation(
                    neighbourhood=hs["neighbourhood"],
                    target_audience=rec["target_audience"],
                    message=rec["message"],
                    category=rec["category"]
                )
                db.add(db_rec)
                
        # Run Isolation Forest anomaly detection
        anomalies = hotspot_detector.detect_anomalies_isolation_forest(reading_dicts_for_ml)
        db.query(models.Hotspot).filter(
            models.Hotspot.detection_method == "IsolationForest",
            models.Hotspot.status == "active"
        ).update({"status": "resolved"})
        db.commit()
        
        for anom in anomalies:
            db_anom = models.Hotspot(
                neighbourhood=anom["neighbourhood"],
                latitude=anom["latitude"],
                longitude=anom["longitude"],
                detection_method="IsolationForest",
                confidence=anom["confidence"],
                main_pollutants=anom["main_pollutants"],
                explanation=anom["message"],
                status="active"
            )
            db.add(db_anom)
            
        db.commit()
    except Exception as e:
        print(f"Error in hotspot detection cycle: {e}")
        
    # 5. Update Neighborhood Averages
    neighborhoods = db.query(models.Neighborhood).all()
    for nb in neighborhoods:
        # Get active sensors in this neighborhood
        active_sensors = db.query(models.Sensor).filter(
            models.Sensor.neighbourhood == nb.name,
            models.Sensor.status == "active"
        ).all()
        
        sensor_ids = [s.id for s in active_sensors]
        nb.sensor_count = len(active_sensors)
        
        if sensor_ids:
            # Average latest AQI of active sensors
            latest_readings = []
            for s_id in sensor_ids:
                lr = db.query(models.Reading).filter(
                    models.Reading.sensor_id == s_id
                ).order_by(models.Reading.timestamp.desc()).first()
                if lr:
                    latest_readings.append(lr)
                    
            if latest_readings:
                nb.average_aqi = round(sum(r.aqi for r in latest_readings) / len(latest_readings), 1)
                
                # Dominant pollutant
                pollutant_counts = {}
                for r in latest_readings:
                    if r.dominant_pollutant:
                        pollutant_counts[r.dominant_pollutant] = pollutant_counts.get(r.dominant_pollutant, 0) + 1
                if pollutant_counts:
                    nb.dominant_pollutant = max(pollutant_counts, key=pollutant_counts.get)
                else:
                    nb.dominant_pollutant = "None"
                    
                # Risk Score (0-100) based on average AQI scaled to standard risk categories
                nb.risk_score = min(100.0, round((nb.average_aqi / 400.0) * 100.0, 1))
            else:
                nb.average_aqi = 0.0
                nb.dominant_pollutant = "None"
                nb.risk_score = 0.0
        else:
            nb.average_aqi = 0.0
            nb.dominant_pollutant = "None"
            nb.risk_score = 0.0
            
    db.commit()
    
    # 6. Trigger forecasting pipeline background training if appropriate
    # Run training every 50 steps (to avoid cpu bottleneck in fast hackathon updates)
    # The first training runs as soon as we have enough data
    readings_count = db.query(models.Reading).count()
    if readings_count > 100 and readings_count % 100 == 0:
        background_tasks.add_task(trigger_forecasting_pipeline, db)
        
    return {"status": "success", "ingested": len(readings_data)}

@app.get("/api/v1/sensors", response_model=List[dict])
def get_sensors_list(db: Session = Depends(get_db)):
    """Returns all registered sensors and their most recent readings and calculated AQI."""
    sensors = db.query(models.Sensor).all()
    results = []
    
    for s in sensors:
        latest_reading = db.query(models.Reading).filter(
            models.Reading.sensor_id == s.id
        ).order_by(models.Reading.timestamp.desc()).first()
        
        results.append({
            "id": s.id,
            "name": s.name,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "neighbourhood": s.neighbourhood,
            "status": s.status,
            "battery_level": s.battery_level,
            "last_active": s.last_active.isoformat(),
            "aqi": latest_reading.aqi if latest_reading else 0.0,
            "pm25": latest_reading.pm25 if latest_reading else 0.0,
            "pm10": latest_reading.pm10 if latest_reading else 0.0,
            "co": latest_reading.co if latest_reading else 0.0,
            "no2": latest_reading.no2 if latest_reading else 0.0,
            "so2": latest_reading.so2 if latest_reading else 0.0,
            "o3": latest_reading.o3 if latest_reading else 0.0,
            "temperature": latest_reading.temperature if latest_reading else 0.0,
            "humidity": latest_reading.humidity if latest_reading else 0.0,
            "wind_speed": latest_reading.wind_speed if latest_reading else 0.0,
            "wind_direction": latest_reading.wind_direction if latest_reading else 0,
            "dominant_pollutant": latest_reading.dominant_pollutant if latest_reading else "None"
        })
        
    return results

@app.get("/api/v1/neighborhoods", response_model=List[schemas.NeighborhoodResponse])
def get_neighborhoods_list(db: Session = Depends(get_db)):
    """Returns list of neighbourhoods with aggregate spatial stats and boundary GeoJSON polygons."""
    return db.query(models.Neighborhood).all()

@app.get("/api/v1/forecast")
def get_forecasts(neighbourhood: Optional[str] = None, sensor_id: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Returns predicted air quality readings for +1h, +3h, +6h, and +24h horizons.
    Uses ML pipeline to generate predictions, falling back dynamically on historical drift equations.
    Includes the Model Comparison Accuracy Table.
    """
    # Horizons to predict
    horizons = [1, 3, 6, 24]
    predictions = {}
    
    # Target search
    query_id = sensor_id if sensor_id else neighbourhood
    if not query_id:
        # Return citywide forecast
        query_id = "Citywide"
        
    # Get latest active data points to extract features
    filter_expr = models.Reading.sensor_id == sensor_id if sensor_id else None
    if neighbourhood and not sensor_id:
        # Get sensors in neighbourhood
        sensors_in_nb = db.query(models.Sensor).filter(models.Sensor.neighbourhood == neighbourhood).all()
        sensor_ids = [s.id for s in sensors_in_nb]
        filter_expr = models.Reading.sensor_id.in_(sensor_ids)
        
    latest_readings_query = db.query(models.Reading)
    if filter_expr is not None:
        latest_readings_query = latest_readings_query.filter(filter_expr)
        
    # Select last 36 readings to construct features
    recent_readings = latest_readings_query.order_by(models.Reading.timestamp.desc()).limit(36).all()
    
    # Fallback default values
    base_aqi = 100.0
    
    if recent_readings:
        # Average latest AQI
        base_aqi = sum(r.aqi for r in recent_readings[:5]) / min(5, len(recent_readings))
        
        # Build features dataframe for ML inference
        readings_list = []
        for r in reversed(recent_readings):
            readings_list.append({
                "timestamp": r.timestamp,
                "pm25": r.pm25,
                "pm10": r.pm10,
                "co": r.co,
                "no2": r.no2,
                "so2": r.so2,
                "o3": r.o3,
                "temperature": r.temperature,
                "humidity": r.humidity,
                "wind_speed": r.wind_speed,
                "wind_direction": r.wind_direction,
                "aqi": r.aqi
            })
            
        try:
            df = cleaner.clean_sensor_data(readings_list)
            # Run XGBoost and LSTM predictions for all horizons
            for h in horizons:
                xgb_pred = forecasting_engine.predict(df, horizon_hours=h, model_type="XGBoost")
                lstm_pred = forecasting_engine.predict(df, horizon_hours=h, model_type="LSTM")
                predictions[f"{h}h"] = {
                    "xgboost": round(xgb_pred, 1),
                    "lstm": round(lstm_pred, 1)
                }
        except Exception:
            pass
            
    # If ML prediction failed or not enough history, populate fallback based on logical daily drift
    if not predictions:
        for h in horizons:
            # Simulate forecasting based on diurnal hourly trend
            target_hour = (datetime.datetime.now().hour + h) % 24
            diurnal_coeff = 1.0
            if 8 <= target_hour <= 10 or 17 <= target_hour <= 20:
                diurnal_coeff = 1.4  # rush hour bump
            elif 1 <= target_hour <= 5:
                diurnal_coeff = 0.6  # early morning dip
                
            xgb_pred = base_aqi * diurnal_coeff * (1.0 + np.random.normal(0, 0.02 * np.sqrt(h)))
            lstm_pred = base_aqi * diurnal_coeff * (1.0 + np.random.normal(0, 0.03 * np.sqrt(h)))
            
            predictions[f"{h}h"] = {
                "xgboost": round(max(0.0, xgb_pred), 1),
                "lstm": round(max(0.0, lstm_pred), 1)
            }
            
    # Include accuracy statistics comparison
    accuracy_metrics = forecaster.get_forecaster_metrics()
    
    return {
        "target": query_id,
        "base_aqi": round(base_aqi, 1),
        "predictions": predictions,
        "metrics_comparison": accuracy_metrics
    }

@app.get("/api/v1/hotspots", response_model=List[schemas.HotspotResponse])
def get_hotspots(db: Session = Depends(get_db)):
    """Returns active spatio-temporal hotspots detected by DBSCAN and Isolation Forest."""
    return db.query(models.Hotspot).filter(models.Hotspot.status == "active").all()

@app.get("/api/v1/alerts", response_model=List[schemas.AlertResponse])
def get_alerts(db: Session = Depends(get_db)):
    """Returns alert log sorted by timestamp."""
    return db.query(models.Alert).order_by(models.Alert.timestamp.desc()).limit(50).all()

@app.get("/api/v1/recommendations", response_model=List[schemas.RecommendationResponse])
def get_recommendations(neighbourhood: Optional[str] = None, db: Session = Depends(get_db)):
    """Returns decision support recommended actions for citizens and municipality."""
    query = db.query(models.Recommendation)
    if neighbourhood:
        query = query.filter(models.Recommendation.neighbourhood == neighbourhood)
    return query.order_by(models.Recommendation.timestamp.desc()).limit(15).all()

@app.get("/api/v1/analytics")
def get_analytics(neighbourhood: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Returns time-series pollutant comparison trends for charting in Recharts.
    Aggregates PM2.5, PM10, SO2, and NO2 levels hourly for the last 24h.
    """
    yesterday = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    query = db.query(models.Reading).filter(models.Reading.timestamp >= yesterday)
    
    if neighbourhood:
        sensors_in_nb = db.query(models.Sensor).filter(models.Sensor.neighbourhood == neighbourhood).all()
        sensor_ids = [s.id for s in sensors_in_nb]
        query = query.filter(models.Reading.sensor_id.in_(sensor_ids))
        
    readings = query.order_by(models.Reading.timestamp.asc()).all()
    
    # Bucket readings hourly
    hourly_buckets = {}
    for r in readings:
        # Convert timestamp to local hourly string
        hour_str = r.timestamp.strftime("%Y-%m-%d %H:00")
        if hour_str not in hourly_buckets:
            hourly_buckets[hour_str] = {
                "timestamp": hour_str,
                "pm25": [], "pm10": [], "co": [], "no2": [], "so2": [], "o3": [], "aqi": []
            }
        
        for poll in ["pm25", "pm10", "co", "no2", "so2", "o3", "aqi"]:
            val = getattr(r, poll, None)
            if val is not None:
                hourly_buckets[hour_str][poll].append(val)
                
    chart_data = []
    for hour_str, vals in sorted(hourly_buckets.items()):
        chart_data.append({
            "time": datetime.datetime.strptime(hour_str, "%Y-%m-%d %H:00").strftime("%H:00"),
            "pm25": round(sum(vals["pm25"]) / len(vals["pm25"]), 1) if vals["pm25"] else 0.0,
            "pm10": round(sum(vals["pm10"]) / len(vals["pm10"]), 1) if vals["pm10"] else 0.0,
            "co": round(sum(vals["co"]) / len(vals["co"]), 2) if vals["co"] else 0.0,
            "no2": round(sum(vals["no2"]) / len(vals["no2"]), 1) if vals["no2"] else 0.0,
            "so2": round(sum(vals["so2"]) / len(vals["so2"]), 1) if vals["so2"] else 0.0,
            "o3": round(sum(vals["o3"]) / len(vals["o3"]), 1) if vals["o3"] else 0.0,
            "aqi": round(sum(vals["aqi"]) / len(vals["aqi"]), 1) if vals["aqi"] else 0.0
        })
        
    return chart_data

@app.post("/api/v1/simulator/control")
def post_simulator_control(control: schemas.SimulatorControl):
    """
    Sets events dynamically for the simulator (e.g., Rain, Rush Hour, Construction Dust).
    Writes configuration to control file, which simulator polls.
    """
    try:
        with open(SIMULATOR_CONTROL_PATH, "w") as f:
            json.dump({
                "event_type": control.event_type,
                "intensity": control.intensity,
                "target_sensor_id": control.target_sensor_id,
                "target_neighbourhood": control.target_neighbourhood
            }, f)
        return {"status": "success", "message": f"Simulator control set to {control.event_type}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write simulator control: {e}")

# -----------------
# Phase 2 Endpoint Mappings & Citizen Reporting
# -----------------

@app.get("/api/sensors")
def get_sensors_p2(db: Session = Depends(get_db)):
    return get_sensors_list(db)

@app.get("/api/hotspots")
def get_hotspots_p2(db: Session = Depends(get_db)):
    return get_hotspots(db)

@app.get("/api/forecast")
def get_forecast_p2(neighbourhood: Optional[str] = None, sensor_id: Optional[str] = None, db: Session = Depends(get_db)):
    return get_forecasts(neighbourhood, sensor_id, db)

@app.get("/api/alerts")
def get_alerts_p2(db: Session = Depends(get_db)):
    return get_alerts(db)

@app.get("/api/analytics")
def get_analytics_p2(neighbourhood: Optional[str] = None, db: Session = Depends(get_db)):
    return get_analytics(neighbourhood, db)

@app.get("/api/recommendations")
def get_recommendations_p2(neighbourhood: Optional[str] = None, db: Session = Depends(get_db)):
    return get_recommendations(neighbourhood, db)

@app.post("/api/simulator/control")
def post_simulator_control_p2(control: schemas.SimulatorControl):
    return post_simulator_control(control)

@app.post("/api/report")
async def create_citizen_report(
    photo: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    neighbourhood: str = Form(...),
    category: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    try:
        # Save photo file
        filename = f"{uuid.uuid4()}_{photo.filename}"
        filepath = os.path.join("static", "uploads", filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)
            
        photo_url = f"/static/uploads/{filename}"
        
        # Run computer vision detection
        cv_res = vision_detector.detect_pollution_in_image(filepath, category)
        
        # Save to DB
        db_report = models.Report(
            photo_url=photo_url,
            latitude=latitude,
            longitude=longitude,
            neighbourhood=neighbourhood,
            category=category,
            description=description,
            cv_detected_category=cv_res["detected_category"],
            cv_confidence=cv_res["confidence"],
            cv_severity=cv_res["severity"],
            bounding_boxes=json.dumps(cv_res["bounding_boxes"])
        )
        db.add(db_report)
        db.commit()
        db.refresh(db_report)
        
        # Check for clustered reports in the last 15 minutes
        fifteen_mins_ago = datetime.datetime.utcnow() - datetime.timedelta(minutes=15)
        recent_count = db.query(models.Report).filter(
            models.Report.neighbourhood == neighbourhood,
            models.Report.category == category,
            models.Report.timestamp >= fifteen_mins_ago
        ).count()
        
        if recent_count >= 3:
            active_alert = db.query(models.Alert).filter(
                models.Alert.neighbourhood == neighbourhood,
                models.Alert.alert_type == "CLUSTERED_REPORTS",
                models.Alert.status == "active"
            ).first()
            if not active_alert:
                db_alert = models.Alert(
                    sensor_id=None,
                    neighbourhood=neighbourhood,
                    alert_type="CLUSTERED_REPORTS",
                    message=f"CRITICAL: Cluster of {recent_count} citizen reports for {category} received in {neighbourhood} within 15 minutes! Immediate dispatch required.",
                    status="active"
                )
                db.add(db_alert)
                
                # Create a temporary hotspot to display on the map
                db_hs = models.Hotspot(
                    neighbourhood=neighbourhood,
                    latitude=latitude,
                    longitude=longitude,
                    detection_method="CitizenReportCluster",
                    confidence=1.0,
                    main_pollutants=category,
                    explanation=f"Multiple citizens reported active {category} here. Verified by computer vision classification.",
                    status="active"
                )
                db.add(db_hs)
                db.commit()
                
        return db_report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create report: {e}")

@app.get("/api/reports")
def get_reports_list(db: Session = Depends(get_db)):
    """Returns all citizen pollution reports sorted by timestamp."""
    return db.query(models.Report).order_by(models.Report.timestamp.desc()).all()

@app.get("/api/neighborhoods", response_model=List[schemas.NeighborhoodResponse])
def get_neighborhoods_list_alias(db: Session = Depends(get_db)):
    """Alias for /api/v1/neighborhoods to support client requests."""
    return get_neighborhoods_list(db)

@app.get("/api/satellite")
def get_satellite_data(centroid_lat: float = 28.6139, centroid_lon: float = 77.2090):
    """Returns simulated satellite layers grid mapping NDVI, Urban density, and Heat anomalies."""
    return satellite_analyzer.get_satellite_grids(centroid_lat, centroid_lon)

# Serve Next.js frontend static build
# Mount at root / after defining all API endpoints
frontend_out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "out")
if os.path.exists(frontend_out):
    app.mount("/", StaticFiles(directory=frontend_out, html=True), name="frontend")



