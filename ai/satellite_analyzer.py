import numpy as np
from typing import List, Dict, Any

def get_satellite_grids(centroid_lat: float = 20.5937, centroid_lon: float = 78.9629) -> List[Dict[str, Any]]:
    """
    Generates simulated satellite-derived information overlays (NDVI, Urban Density, Heat)
    centered around major Indian metro centers to overlay correctly on the map.
    """
    grid_cells = []
    
    # Neighborhood centers to generate grids around (spanning India)
    neighborhoods_centers = {
        "Industrial Zone": (28.6139, 77.2090),          # Delhi NCR
        "Downtown Business District": (19.0760, 72.8777), # Mumbai
        "Residential East": (22.5726, 88.3639),           # Kolkata
        "Green Valley Park": (12.9716, 77.5946),          # Bengaluru
        "Construction Site North": (13.0827, 80.2707),   # Chennai
        "Suburbs West": (17.3850, 78.4867)               # Hyderabad
    }

    for nb_name, center in neighborhoods_centers.items():
        lat, lon = center
        # Spanning 0.1 degree grid around each city center
        lat_min, lat_max = lat - 0.05, lat + 0.05
        lon_min, lon_max = lon - 0.05, lon + 0.05
        
        rows, cols = 3, 3
        lat_step = (lat_max - lat_min) / rows
        lon_step = (lon_max - lon_min) / cols
        
        for r in range(rows):
            for c in range(cols):
                cell_lat_min = lat_min + r * lat_step
                cell_lat_max = cell_lat_min + lat_step
                cell_lon_min = lon_min + c * lon_step
                cell_lon_max = cell_lon_min + lon_step
                
                # Default values
                ndvi = 0.35
                urban_density = 0.5
                thermal_anomaly = False
                
                # Set satellite attributes based on neighborhood characteristics
                if nb_name == "Green Valley Park":
                    ndvi = 0.82 + np.random.uniform(-0.05, 0.05)
                    urban_density = 0.15
                elif nb_name == "Industrial Zone":
                    ndvi = 0.18 + np.random.uniform(-0.03, 0.03)
                    urban_density = 0.70
                    if np.random.random() < 0.15:
                        thermal_anomaly = True
                elif nb_name == "Downtown Business District":
                    ndvi = 0.22
                    urban_density = 0.88 + np.random.uniform(-0.05, 0.05)
                elif nb_name == "Construction Site North":
                    ndvi = 0.15
                    urban_density = 0.45
                    if np.random.random() < 0.1:
                        thermal_anomaly = True
                elif nb_name == "Residential East":
                    ndvi = 0.45
                    urban_density = 0.65
                else: # Suburbs West
                    ndvi = 0.52
                    urban_density = 0.35
                    
                grid_cells.append({
                    "id": f"cell-{nb_name.replace(' ', '_')}-{r}-{c}",
                    "bounds": [
                        [float(cell_lat_min), float(cell_lon_min)], # SW
                        [float(cell_lat_max), float(cell_lon_min)], # NW
                        [float(cell_lat_max), float(cell_lon_max)], # NE
                        [float(cell_lat_min), float(cell_lon_max)]  # SE
                    ],
                    "ndvi": float(round(ndvi, 3)),
                    "urban_density": float(round(urban_density, 3)),
                    "thermal_anomaly": thermal_anomaly,
                    "dominant_neighborhood": nb_name
                })
                
    return grid_cells
