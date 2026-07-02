from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
import datetime
from .database import Base

class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    neighbourhood = Column(String, nullable=False, index=True)
    status = Column(String, default="active")  # active, offline, drifting, failing
    battery_level = Column(Float, default=100.0)
    last_active = Column(DateTime, default=datetime.datetime.utcnow)

    readings = relationship("Reading", back_populates="sensor", cascade="all, delete-orphan")

class Reading(Base):
    __tablename__ = "readings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sensor_id = Column(String, ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    
    # Pollutants
    pm25 = Column(Float, nullable=True)
    pm10 = Column(Float, nullable=True)
    co = Column(Float, nullable=True)
    no2 = Column(Float, nullable=True)
    so2 = Column(Float, nullable=True)
    o3 = Column(Float, nullable=True)
    
    # Meteorological Data
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    pressure = Column(Float, nullable=True)
    wind_speed = Column(Float, nullable=True)
    wind_direction = Column(Float, nullable=True)
    
    # Device State
    battery_level = Column(Float, nullable=True)
    
    # Calculated AQI
    aqi = Column(Float, nullable=True)
    dominant_pollutant = Column(String, nullable=True)

    sensor = relationship("Sensor", back_populates="readings")

class Neighborhood(Base):
    __tablename__ = "neighborhoods"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False, index=True)
    boundary_geojson = Column(Text, nullable=False)  # GeoJSON string defining the boundary
    average_aqi = Column(Float, default=0.0)
    dominant_pollutant = Column(String, nullable=True)
    risk_score = Column(Float, default=0.0)  # Calculated risk score (0-100)
    sensor_count = Column(Integer, default=0)

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sensor_id = Column(String, nullable=True, index=True)
    neighbourhood = Column(String, nullable=True, index=True)
    alert_type = Column(String, nullable=False)  # AQI_EXCEED, SPIKE, SENSOR_FAILURE, FORECAST_HOTSPOT
    message = Column(String, nullable=False)
    status = Column(String, default="active")  # active, resolved
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sensor_id = Column(String, nullable=True, index=True)
    neighbourhood = Column(String, nullable=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    target_time = Column(DateTime, nullable=False)
    horizon_hours = Column(Integer, nullable=False)  # 1, 3, 6, 24
    predicted_aqi = Column(Float, nullable=False)
    predicted_pm25 = Column(Float, nullable=True)
    predicted_pm10 = Column(Float, nullable=True)
    model_type = Column(String, nullable=False)  # XGBoost, LSTM

class Hotspot(Base):
    __tablename__ = "hotspots"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    neighbourhood = Column(String, nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    detection_method = Column(String, nullable=False)  # DBSCAN, IsolationForest
    confidence = Column(Float, default=1.0)
    main_pollutants = Column(String, nullable=True)  # Comma-separated list
    explanation = Column(Text, nullable=True)
    status = Column(String, default="active")  # active, resolved
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    neighbourhood = Column(String, nullable=False, index=True)
    target_audience = Column(String, nullable=False)  # Citizen, Municipality
    message = Column(Text, nullable=False)
    category = Column(String, nullable=False)  # Health, Operations, Traffic
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    photo_url = Column(String, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    neighbourhood = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    cv_detected_category = Column(String, nullable=True)
    cv_confidence = Column(Float, nullable=True)
    cv_severity = Column(String, nullable=True)
    bounding_boxes = Column(Text, nullable=True) # JSON string representation

