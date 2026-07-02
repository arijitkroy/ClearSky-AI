import numpy as np
from typing import List, Dict, Any

def get_satellite_grids(centroid_lat: float = 28.6139, centroid_lon: float = 77.2090) -> List[Dict[str, Any]]:
    """
    Generates a 10x10 grid of simulated satellite-derived information overlays
    including NDVI (vegetation), Urban Density, and Thermal Anomalies (FIRMS).
    """
    grid_cells = []
    
    # Grid boundaries spanning the New Delhi centroid
    lat_min, lat_max = centroid_lat - 0.1, centroid_lat + 0.1
    lon_min, lon_max = centroid_lon - 0.15, centroid_lon + 0.15
    
    rows, cols = 10, 10
    lat_step = (lat_max - lat_min) / rows
    lon_step = (lon_max - lon_min) / cols
    
    # Neighborhood centers to align values
    neighborhoods_centers = {
        "Industrial Zone": (28.6500, 77.1200),
        "Downtown Business District": (28.6300, 77.2200),
        "Residential East": (28.6200, 77.2800),
        "Green Valley Park": (28.5800, 77.2100),
        "Construction Site North": (28.6900, 77.1800),
        "Suburbs West": (28.6100, 77.0800)
    }

    for r in range(rows):
        for c in range(cols):
            cell_lat_min = lat_min + r * lat_step
            cell_lat_max = cell_lat_min + lat_step
            cell_lon_min = lon_min + c * lon_step
            cell_lon_max = cell_lon_min + lon_step
            
            # Midpoint coordinate
            mid_lat = cell_lat_min + (lat_step / 2)
            mid_lon = cell_lon_min + (lon_step / 2)
            
            # Calculate distance to neighborhoods to determine realistic satellite stats
            ndvi = 0.35 # baseline grass
            urban_density = 0.5
            thermal_anomaly = False
            
            # Find nearest neighborhood profile
            min_dist = float("inf")
            nearest_nb = "Suburbs West"
            
            for nb_name, center in neighborhoods_centers.items():
                dist = np.sqrt((mid_lat - center[0])**2 + (mid_lon - center[1])**2)
                if dist < min_dist:
                    min_dist = dist
                    nearest_nb = nb_name
                    
            # Set satellite attributes based on nearest neighborhood characteristics
            if nearest_nb == "Green Valley Park":
                ndvi = 0.82 + np.random.uniform(-0.05, 0.05) # high vegetation
                urban_density = 0.15
            elif nearest_nb == "Industrial Zone":
                ndvi = 0.18 + np.random.uniform(-0.03, 0.03) # low vegetation
                urban_density = 0.70
                # Occasional simulated thermal hotspot
                if np.random.random() < 0.15:
                    thermal_anomaly = True
            elif nearest_nb == "Downtown Business District":
                ndvi = 0.22
                urban_density = 0.88 + np.random.uniform(-0.05, 0.05) # high density concrete
            elif nearest_nb == "Construction Site North":
                ndvi = 0.15
                urban_density = 0.45
                if np.random.random() < 0.1:
                    thermal_anomaly = True
            elif nearest_nb == "Residential East":
                ndvi = 0.45
                urban_density = 0.65
            else: # Suburbs West
                ndvi = 0.52
                urban_density = 0.35
                
            grid_cells.append({
                "id": f"cell-{r}-{c}",
                "bounds": [
                    [float(cell_lat_min), float(cell_lon_min)], # SW
                    [float(cell_lat_max), float(cell_lon_min)], # NW
                    [float(cell_lat_max), float(cell_lon_max)], # NE
                    [float(cell_lat_min), float(cell_lon_max)]  # SE
                ],
                "ndvi": float(round(ndvi, 3)),
                "urban_density": float(round(urban_density, 3)),
                "thermal_anomaly": thermal_anomaly,
                "dominant_neighborhood": nearest_nb
            })
            
    return grid_cells
