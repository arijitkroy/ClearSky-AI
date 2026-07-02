import pandas as pd
import numpy as np
from typing import List, Dict, Any, Union

def handle_missing_values(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    """
    Interpolate missing values for given columns.
    Uses linear interpolation, falls back to forward-fill, then backward-fill, then 0.
    """
    df = df.copy()
    for col in columns:
        if col in df.columns:
            # Interpolate
            df[col] = df[col].interpolate(method="linear", limit_direction="both")
            # Fallback ffill and bfill
            df[col] = df[col].ffill().bfill().fillna(0.0)
    return df

def detect_and_replace_outliers(df: pd.DataFrame, columns: List[str], threshold: float = 3.0) -> pd.DataFrame:
    """
    Detect outliers using rolling z-score and replace them with NaN, 
    then interpolate to clean them.
    """
    df = df.copy()
    for col in columns:
        if col in df.columns and len(df) > 3:
            # Calculate rolling mean and std
            rolling_mean = df[col].rolling(window=12, min_periods=1, center=True).mean()
            rolling_std = df[col].rolling(window=12, min_periods=1, center=True).std()
            
            # Prevent division by zero
            rolling_std = rolling_std.replace(0, 1e-6)
            
            # Calculate z-score
            z_scores = (df[col] - rolling_mean) / rolling_std
            
            # Identify outliers (Z-score > threshold) and set to NaN
            outliers = np.abs(z_scores) > threshold
            df.loc[outliers, col] = np.nan
            
            # Interpolate the newly created NaNs
            df[col] = df[col].interpolate(method="linear", limit_direction="both").fillna(rolling_mean)
    return df

def add_rolling_averages(df: pd.DataFrame, columns: List[str], windows: List[int] = [3, 24]) -> pd.DataFrame:
    """
    Calculate rolling averages for given windows (in hours, assuming 1 row per hour/timestamp).
    For high-frequency sensor readings (e.g. every 5s), windows should be in counts of readings.
    """
    df = df.copy()
    for col in columns:
        if col in df.columns:
            for w in windows:
                df[f"{col}_roll_{w}"] = df[col].rolling(window=w, min_periods=1).mean()
    return df

def normalize_features(df: pd.DataFrame, columns: List[str]) -> tuple[pd.DataFrame, dict]:
    """
    Normalize columns using Min-Max scaling. Returns the df and a dict of min/max values.
    """
    df = df.copy()
    params = {}
    for col in columns:
        if col in df.columns:
            c_min = df[col].min()
            c_max = df[col].max()
            if c_max == c_min:
                c_max += 1e-6
            df[col] = (df[col] - c_min) / (c_max - c_min)
            params[col] = {"min": float(c_min), "max": float(c_max)}
    return df, params

def clean_sensor_data(readings_list: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Entire cleaning pipeline for raw reading dictionaries.
    Converts list of dicts to a clean pandas DataFrame.
    """
    if not readings_list:
        return pd.DataFrame()
        
    df = pd.DataFrame(readings_list)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")
        
    pollutants = ["pm25", "pm10", "co", "no2", "so2", "o3"]
    met_data = ["temperature", "humidity", "pressure", "wind_speed", "wind_direction"]
    cols_to_clean = pollutants + met_data
    
    # Clean only columns that exist
    existing_cols = [c for c in cols_to_clean if c in df.columns]
    
    df = handle_missing_values(df, existing_cols)
    df = detect_and_replace_outliers(df, existing_cols)
    df = add_rolling_averages(df, [c for c in ["pm25", "pm10"] if c in df.columns], windows=[3, 12, 24])
    
    return df
