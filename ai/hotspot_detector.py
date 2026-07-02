import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.ensemble import IsolationForest
from typing import List, Dict, Any, Tuple

def detect_hotspots_dbscan(
    sensor_data: List[Dict[str, Any]], 
    aqi_threshold: float = 120.0, 
    eps_degrees: float = 0.015,  # Approx 1.5 km
    min_samples: int = 2
) -> List[Dict[str, Any]]:
    """
    Detects spatial clusters of highly polluted sensors using DBSCAN.
    Only sensors with AQI > aqi_threshold are clustered.
    """
    if not sensor_data or len(sensor_data) < min_samples:
        return []

    # Filter sensors above the AQI threshold
    high_aqi_sensors = [s for s in sensor_data if s.get("aqi", 0) >= aqi_threshold]
    
    if len(high_aqi_sensors) < min_samples:
        return []

    # Prepare features for spatial clustering: [longitude, latitude]
    coords = np.array([[s["longitude"], s["latitude"]] for s in high_aqi_sensors])
    
    # Run DBSCAN
    db = DBSCAN(eps=eps_degrees, min_samples=min_samples).fit(coords)
    labels = db.labels_
    
    hotspots = []
    unique_labels = set(labels)
    
    for label in unique_labels:
        if label == -1:
            # Noise points (isolated sensors above threshold)
            continue
            
        # Get coordinates of cluster members
        cluster_mask = (labels == label)
        cluster_coords = coords[cluster_mask]
        cluster_sensors = [high_aqi_sensors[i] for i, mask in enumerate(cluster_mask) if mask]
        
        # Calculate cluster center
        center_lon, center_lat = np.mean(cluster_coords, axis=0)
        
        # Calculate average AQI of cluster
        avg_aqi = float(np.mean([s["aqi"] for s in cluster_sensors]))
        
        # Find dominant pollutants
        pollutant_vals = {}
        for s in cluster_sensors:
            for p in ["pm25", "pm10", "no2", "so2", "co", "o3"]:
                if s.get(p) is not None:
                    pollutant_vals[p] = pollutant_vals.get(p, []) + [s[p]]
                    
        main_pollutants = []
        for p, vals in pollutant_vals.items():
            if np.mean(vals) > 50:  # Threshold for considering it a primary driver
                main_pollutants.append(p)
                
        # Neighborhoods representing this cluster
        neighbourhoods = list(set([s["neighbourhood"] for s in cluster_sensors]))
        
        hotspots.append({
            "neighbourhood": neighbourhoods[0] if neighbourhoods else "Unknown",
            "latitude": float(center_lat),
            "longitude": float(center_lon),
            "detection_method": "DBSCAN",
            "confidence": min(1.0, len(cluster_sensors) / 5.0),
            "main_pollutants": ", ".join(main_pollutants) if main_pollutants else "aqi",
            "sensor_count": len(cluster_sensors),
            "avg_aqi": avg_aqi
        })
        
    return hotspots

def detect_anomalies_isolation_forest(
    sensor_data: List[Dict[str, Any]], 
    contamination: float = 0.05
) -> List[Dict[str, Any]]:
    """
    Detects individual sensor anomalies (spikes/drift) using Isolation Forest.
    Returns flagged sensors.
    """
    if len(sensor_data) < 5:
        return []
        
    df = pd.DataFrame(sensor_data)
    
    # Select features for anomaly detection
    features = ["pm25", "pm10", "co", "no2", "so2", "o3", "temperature", "humidity", "wind_speed"]
    available_features = [f for f in features if f in df.columns]
    
    if not available_features:
        return []
        
    # Impute missing values with column median
    X = df[available_features].fillna(df[available_features].median()).values
    
    # Run Isolation Forest
    clf = IsolationForest(contamination=contamination, random_state=42)
    y_pred = clf.fit_predict(X)
    
    # Flagged anomalies (y_pred == -1)
    anomalies = []
    for idx, pred in enumerate(y_pred):
        if pred == -1:
            sensor = sensor_data[idx]
            # Calculate anomaly score (lower is more anomalous)
            score = float(clf.decision_function(X[idx].reshape(1, -1))[0])
            confidence = float(np.clip(1.0 - abs(score) * 2, 0.5, 1.0))
            
            # Determine main pollutant driving the anomaly
            # By looking at how much standard deviations it is from feature mean
            feat_means = np.mean(X, axis=0)
            feat_stds = np.std(X, axis=0) + 1e-6
            z_scores = (X[idx] - feat_means) / feat_stds
            
            max_idx = np.argmax(z_scores)
            main_driver = available_features[max_idx]
            
            anomalies.append({
                "sensor_id": sensor["id"],
                "neighbourhood": sensor["neighbourhood"],
                "latitude": float(sensor["latitude"]),
                "longitude": float(sensor["longitude"]),
                "detection_method": "IsolationForest",
                "confidence": confidence,
                "main_pollutants": main_driver,
                "aqi": sensor.get("aqi", 0),
                "message": f"Anomalous reading detected on {sensor['id']} driven by {main_driver}"
            })
            
    return anomalies

def compare_hotspot_detectors(sensor_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Runs both DBSCAN and Isolation Forest and returns a comparison summary.
    """
    dbscan_hotspots = detect_hotspots_dbscan(sensor_data)
    iforest_anomalies = detect_anomalies_isolation_forest(sensor_data)
    
    # Calculate overlap
    overlapping_sensors = []
    dbscan_neighbourhoods = [h["neighbourhood"] for h in dbscan_hotspots]
    
    for anomaly in iforest_anomalies:
        if anomaly["neighbourhood"] in dbscan_neighbourhoods:
            overlapping_sensors.append(anomaly["sensor_id"])
            
    return {
        "dbscan_count": len(dbscan_hotspots),
        "iforest_count": len(iforest_anomalies),
        "overlap_count": len(overlapping_sensors),
        "overlapping_sensors": overlapping_sensors,
        "dbscan_details": dbscan_hotspots,
        "iforest_details": iforest_anomalies
    }
