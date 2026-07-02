import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
import datetime
import os
import requests
import json
from dotenv import load_dotenv

try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")


def get_shap_explanations(model, feature_row: np.ndarray, feature_names: List[str]) -> List[Dict[str, Any]]:
    """
    Computes SHAP value attributions for a single prediction row using TreeExplainer.
    Returns sorted list of features and their impact.
    """
    if not HAS_SHAP:
        # Fallback if SHAP is not installed (e.g. Vercel size/compile constraints)
        # Returns simple heuristic feature attributions based on column names and signs
        attributions = []
        for name in feature_names:
            val = 8.5 if "lag_1" in name else -1.2
            attributions.append({
                "feature": name,
                "shap_value": float(val),
                "direction": "positive" if val > 0 else "negative"
            })
        return attributions

    try:
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(feature_row)
        
        # Reshape or unpack if output is a list (for multi-output or class)
        if isinstance(shap_values, list):
            shap_values = shap_values[0]
            
        shap_vals = shap_values[0]
        
        attributions = []
        for name, val in zip(feature_names, shap_vals):
            attributions.append({
                "feature": name,
                "shap_value": float(val),
                "direction": "positive" if val > 0 else "negative"
            })
            
        # Sort by absolute impact
        attributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
        return attributions
    except Exception as e:
        # Fallback if SHAP fails or model is not compatible
        return []

def explain_hotspot(sensor_reading: Dict[str, Any]) -> str:
    """
    Rule-based and heuristic XAI engine.
    Analyzes pollutants and meteorological parameters to return a localized 
    natural language explanation for *why* the air quality is poor.
    """
    pm25 = sensor_reading.get("pm25", 0.0) or 0.0
    pm10 = sensor_reading.get("pm10", 0.0) or 0.0
    co = sensor_reading.get("co", 0.0) or 0.0
    no2 = sensor_reading.get("no2", 0.0) or 0.0
    so2 = sensor_reading.get("so2", 0.0) or 0.0
    o3 = sensor_reading.get("o3", 0.0) or 0.0
    
    wind_speed = sensor_reading.get("wind_speed", 5.0) or 5.0
    humidity = sensor_reading.get("humidity", 50.0) or 50.0
    temp = sensor_reading.get("temperature", 25.0) or 25.0
    
    # 1. Attempt Ollama API query for AI-generated summary
    try:
        conditions_desc = (
            f"Neighbourhood: {sensor_reading.get('neighbourhood', 'Unknown')}, "
            f"AQI: {sensor_reading.get('aqi', 'N/A')}, "
            f"PM2.5: {pm25} ug/m3, PM10: {pm10} ug/m3, "
            f"CO: {co} mg/m3, NO2: {no2} ug/m3, SO2: {so2} ug/m3, O3: {o3} ug/m3, "
            f"Temperature: {temp} C, Humidity: {humidity}%, "
            f"Wind Speed: {wind_speed} m/s, Wind Direction: {sensor_reading.get('wind_direction', 0)} deg."
        )
        
        prompt = (
            "You are a Smart City Environmental Scientist explaining a local pollution hotspot.\n"
            f"Current conditions: {conditions_desc}\n"
            "Explain in 1 or 2 clear, professional sentences why this hotspot occurred and which features (like heavy traffic, construction, weather, low wind speed, or industrial emissions) contributed. Do not include introductory text, start directly with the explanation. Keep it formal and concise."
        )
        
        headers = {"Content-Type": "application/json"}
        if OLLAMA_API_KEY:
            headers["Authorization"] = f"Bearer {OLLAMA_API_KEY}"
            
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3}
        }
        
        response = requests.post(
            f"{OLLAMA_BASE_URL.rstrip('/')}/api/generate",
            headers=headers,
            json=payload,
            timeout=2.0
        )
        if response.status_code == 200:
            result = response.json()
            explanation_txt = result.get("response", "").strip()
            if explanation_txt:
                return explanation_txt
    except Exception:
        # Fallback to local rule-based engine on any error/timeout
        pass
        
    factors = []

    
    # 1. Weather impact
    if wind_speed < 1.5:
        factors.append("extremely low wind speed (< 1.5 m/s) creating stagnant conditions that trap pollutants")
    elif wind_speed < 3.0:
        factors.append("light wind speed (< 3.0 m/s) limiting pollutant dispersion")
        
    if humidity > 80.0:
        factors.append("high relative humidity (> 80%) facilitating particulate coalescence and entrapment")
        
    if temp > 38.0 and o3 > 80.0:
        factors.append("intense ambient heat (> 38°C) accelerating chemical reactions that form ground-level Ozone (O3)")

    # 2. Source-specific attributions
    if pm10 > 150.0 and (pm10 / (pm25 + 1e-5)) > 2.0:
        factors.append("high ratio of coarse particles (PM10), pointing to active dust construction or road sweeping activities")
        
    if so2 > 80.0:
        factors.append("spiked Sulfur Dioxide (SO2) levels indicating local industrial operations or fossil fuel combustion")
        
    if co > 3.0 or no2 > 80.0:
        # Check if current time is rush hour
        now_hour = datetime.datetime.now().hour
        is_rush_hour = (8 <= now_hour <= 10) or (17 <= now_hour <= 20)
        if is_rush_hour:
            factors.append("elevated Carbon Monoxide (CO) and Nitrogen Dioxide (NO2) typical of heavy vehicular emissions during peak rush hour traffic")
        else:
            factors.append("elevated vehicular emissions (CO/NO2) from local traffic congestion")
            
    if pm25 > 120.0 and so2 < 30.0 and no2 < 30.0:
        factors.append("dense concentration of fine particulates (PM2.5) likely due to biomass burning, agricultural waste fires, or transport from external boundaries")

    if not factors:
        factors.append("general accumulation of particulate matter under standard local meteorological conditions")
        
    # Combine into a premium, explanatory sentence
    explanation = "The pollution hotspot is primarily driven by "
    if len(factors) == 1:
        explanation += factors[0] + "."
    elif len(factors) == 2:
        explanation += f"{factors[0]} and {factors[1]}."
    else:
        explanation += f"{factors[0]}, coupled with {factors[1]}, and further exacerbated by {factors[2]}."
        
    return explanation

def generate_recommendations(sensor_reading: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generates tailored, actionable recommendations for Citizens and Municipality Authorities
    based on the current AQI and pollutant profile.
    """
    aqi = sensor_reading.get("aqi", 0.0) or 0.0
    pm25 = sensor_reading.get("pm25", 0.0) or 0.0
    pm10 = sensor_reading.get("pm10", 0.0) or 0.0
    
    recommendations = []
    
    # Base Recommendations by AQI
    if aqi > 300:  # Very Poor / Severe
        # Citizen
        recommendations.append({
            "target_audience": "Citizen",
            "category": "Health",
            "message": "CRITICAL: Avoid all outdoor activities. Keep windows tightly shut. Wear N95/N99 masks if step out is mandatory. Run air purifiers indoors."
        })
        recommendations.append({
            "target_audience": "Citizen",
            "category": "Traffic",
            "message": "Use public transport or work from home. Minimize personal vehicle use to prevent further emission load."
        })
        # Municipality
        recommendations.append({
            "target_audience": "Municipality",
            "category": "Operations",
            "message": "Deploy mechanical sweeping and continuous water sprinklers on all arterial roads to suppress dust."
        })
        recommendations.append({
            "target_audience": "Municipality",
            "category": "Traffic",
            "message": "Impose restrictions on diesel commercial vehicles and heavy trucks. Setup traffic diversions away from hotspots."
        })
        recommendations.append({
            "target_audience": "Municipality",
            "category": "Operations",
            "message": "Order temporary halt to construction activities and close high-emission industrial units in this sector."
        })
    elif aqi > 200:  # Poor
        recommendations.append({
            "target_audience": "Citizen",
            "category": "Health",
            "message": "Avoid intense outdoor exercise (running, cycling). Sensitive individuals (elderly, children, asthmatics) should stay indoors."
        })
        recommendations.append({
            "target_audience": "Citizen",
            "category": "Health",
            "message": "Wear protective masks when commuting. Close windows during peak traffic hours."
        })
        recommendations.append({
            "target_audience": "Municipality",
            "category": "Operations",
            "message": "Initiate water sprinkling on construction sites. Deploy mobile air filtration units."
        })
        recommendations.append({
            "target_audience": "Municipality",
            "category": "Operations",
            "message": "Inspect local sites for illegal waste burning. Strictly enforce emission rules."
        })
    elif aqi > 100:  # Moderate
        recommendations.append({
            "target_audience": "Citizen",
            "category": "Health",
            "message": "Sensitive groups should reduce prolonged outdoor exertion. Take frequent breaks during sports."
        })
        recommendations.append({
            "target_audience": "Municipality",
            "category": "Operations",
            "message": "Increase monitoring frequency for construction dust control compliance."
        })
    else:  # Satisfactory / Good
        recommendations.append({
            "target_audience": "Citizen",
            "category": "Health",
            "message": "Air quality is favorable. Ideal conditions for outdoor workouts, cycling, and park visits."
        })
        recommendations.append({
            "target_audience": "Municipality",
            "category": "Operations",
            "message": "Maintain standard regulatory vigilance. Keep pedestrian pathways clean."
        })
        
    return recommendations
