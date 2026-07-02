from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Sensor Schemas
class SensorBase(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    neighbourhood: str

class SensorCreate(SensorBase):
    status: Optional[str] = "active"
    battery_level: Optional[float] = 100.0

class SensorResponse(SensorBase):
    status: str
    battery_level: float
    last_active: datetime

    class Config:
        from_attributes = True

# Reading Schemas
class ReadingBase(BaseModel):
    sensor_id: str
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    co: Optional[float] = None
    no2: Optional[float] = None
    so2: Optional[float] = None
    o3: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    pressure: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None
    battery_level: Optional[float] = None

class ReadingCreate(ReadingBase):
    timestamp: Optional[datetime] = None

class ReadingResponse(ReadingBase):
    id: int
    timestamp: datetime
    aqi: Optional[float] = None
    dominant_pollutant: Optional[str] = None

    class Config:
        from_attributes = True

# Neighborhood Schemas
class NeighborhoodBase(BaseModel):
    name: str
    boundary_geojson: str

class NeighborhoodCreate(NeighborhoodBase):
    pass

class NeighborhoodResponse(NeighborhoodBase):
    id: int
    average_aqi: float
    dominant_pollutant: Optional[str] = None
    risk_score: float
    sensor_count: int

    class Config:
        from_attributes = True

# Alert Schemas
class AlertBase(BaseModel):
    sensor_id: Optional[str] = None
    neighbourhood: Optional[str] = None
    alert_type: str
    message: str
    status: Optional[str] = "active"

class AlertCreate(AlertBase):
    pass

class AlertResponse(AlertBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

# Prediction Schemas
class PredictionBase(BaseModel):
    sensor_id: Optional[str] = None
    neighbourhood: Optional[str] = None
    target_time: datetime
    horizon_hours: int
    predicted_aqi: float
    predicted_pm25: Optional[float] = None
    predicted_pm10: Optional[float] = None
    model_type: str

class PredictionCreate(PredictionBase):
    pass

class PredictionResponse(PredictionBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

# Hotspot Schemas
class HotspotBase(BaseModel):
    neighbourhood: str
    latitude: float
    longitude: float
    detection_method: str
    confidence: float
    main_pollutants: Optional[str] = None
    explanation: Optional[str] = None
    status: Optional[str] = "active"

class HotspotCreate(HotspotBase):
    pass

class HotspotResponse(HotspotBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

# Recommendation Schemas
class RecommendationBase(BaseModel):
    neighbourhood: str
    target_audience: str
    message: str
    category: str

class RecommendationCreate(RecommendationBase):
    pass

class RecommendationResponse(RecommendationBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

# Simulator Controls
class SimulatorControl(BaseModel):
    event_type: str  # "rain", "rush_hour", "construction", "sensor_failure", "normal"
    intensity: Optional[float] = 1.0  # level of intensity (0.0 to 1.0)
    target_sensor_id: Optional[str] = None
    target_neighbourhood: Optional[str] = None

# Report Schemas
class ReportBase(BaseModel):
    latitude: float
    longitude: float
    neighbourhood: str
    category: str
    description: Optional[str] = None

class ReportCreate(ReportBase):
    photo_url: Optional[str] = None

class ReportResponse(ReportBase):
    id: int
    photo_url: Optional[str] = None
    timestamp: datetime
    cv_detected_category: Optional[str] = None
    cv_confidence: Optional[float] = None
    cv_severity: Optional[str] = None
    bounding_boxes: Optional[str] = None

    class Config:
        from_attributes = True

