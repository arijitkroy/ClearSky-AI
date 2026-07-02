# CPCB AQI Calculation module according to Central Pollution Control Board (India) standards

# Breakpoints and index values
BREAKPOINTS = {
    "pm25": [
        (0.0, 30.0, 0.0, 50.0),
        (30.1, 60.0, 51.0, 100.0),
        (60.1, 90.0, 101.0, 200.0),
        (90.1, 120.0, 201.0, 300.0),
        (120.1, 250.0, 301.0, 400.0),
        (250.1, 500.0, 401.0, 500.0)
    ],
    "pm10": [
        (0.0, 50.0, 0.0, 50.0),
        (50.1, 100.0, 51.0, 100.0),
        (100.1, 250.0, 101.0, 200.0),
        (250.1, 350.0, 201.0, 300.0),
        (350.1, 430.0, 301.0, 400.0),
        (430.1, 500.0, 401.0, 500.0)
    ],
    "no2": [
        (0.0, 40.0, 0.0, 50.0),
        (40.1, 80.0, 51.0, 100.0),
        (80.1, 180.0, 101.0, 200.0),
        (180.1, 280.0, 201.0, 300.0),
        (280.1, 400.0, 301.0, 400.0),
        (400.1, 1000.0, 401.0, 500.0)
    ],
    "so2": [
        (0.0, 40.0, 0.0, 50.0),
        (40.1, 80.0, 51.0, 100.0),
        (80.1, 380.0, 101.0, 200.0),
        (380.1, 800.0, 201.0, 300.0),
        (801.0, 1600.0, 301.0, 400.0),
        (1600.1, 3000.0, 401.0, 500.0)
    ],
    "co": [
        (0.0, 1.0, 0.0, 50.0),
        (1.01, 2.0, 51.0, 100.0),
        (2.01, 10.0, 101.0, 200.0),
        (10.01, 17.0, 201.0, 300.0),
        (17.01, 34.0, 301.0, 400.0),
        (34.01, 100.0, 401.0, 500.0)
    ],
    "o3": [
        (0.0, 50.0, 0.0, 50.0),
        (50.1, 100.0, 51.0, 100.0),
        (100.1, 168.0, 101.0, 200.0),
        (168.1, 208.0, 201.0, 300.0),
        (208.1, 748.0, 301.0, 400.0),
        (748.1, 1000.0, 401.0, 500.0)
    ]
}

def calculate_sub_index(pollutant: str, concentration: float) -> float:
    """Calculates sub-index for a single pollutant based on CPCB standards."""
    if concentration is None or concentration < 0:
        return 0.0

    if pollutant not in BREAKPOINTS:
        return 0.0

    for b_low, b_high, i_low, i_high in BREAKPOINTS[pollutant]:
        if b_low <= concentration <= b_high:
            # Piecewise linear formula
            return round(((i_high - i_low) / (b_high - b_low)) * (concentration - b_low) + i_low, 1)

    # If concentration exceeds upper bound of severest class, extrapolate or return max 500
    last_bp = BREAKPOINTS[pollutant][-1]
    if concentration > last_bp[1]:
        return 500.0

    return 0.0

def get_aqi_category(aqi: float) -> str:
    """Returns CPCB AQI Category name based on AQI value."""
    if aqi <= 50:
        return "Good"
    elif aqi <= 100:
        return "Satisfactory"
    elif aqi <= 200:
        return "Moderate"
    elif aqi <= 300:
        return "Poor"
    elif aqi <= 400:
        return "Very Poor"
    else:
        return "Severe"

def get_aqi_color(aqi: float) -> str:
    """Returns HEX/standard CSS colors for a given AQI level."""
    if aqi <= 50:
        return "green"
    elif aqi <= 100:
        return "light-green"
    elif aqi <= 200:
        return "yellow"
    elif aqi <= 300:
        return "orange"
    elif aqi <= 400:
        return "red"
    else:
        return "maroon"

def calculate_overall_aqi(readings: dict) -> tuple[float, str]:
    """
    Computes overall AQI from a dict of pollutant concentrations.
    Returns: (aqi_value, dominant_pollutant)
    """
    sub_indices = {}
    for pollutant in ["pm25", "pm10", "no2", "so2", "co", "o3"]:
        if pollutant in readings and readings[pollutant] is not None:
            sub_indices[pollutant] = calculate_sub_index(pollutant, readings[pollutant])

    if not sub_indices:
        return 0.0, "None"

    # In CPCB, overall AQI is the maximum sub-index
    # Technically needs at least 3 monitored pollutants, including PM2.5 or PM10
    # For a robust prototype, we take max of any available sub-indices
    max_pollutant = max(sub_indices, key=sub_indices.get)
    max_aqi = sub_indices[max_pollutant]

    return float(max_aqi), max_pollutant
