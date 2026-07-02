import { useEffect } from "react";
import { MapContainer, TileLayer, Polygon, CircleMarker, Popup, useMap } from "react-leaflet";
import L from "leaflet";

const getApiBaseUrl = () => {
  if (process.env.NEXT_PUBLIC_API_URL && process.env.NEXT_PUBLIC_API_URL !== "http://127.0.0.1:8000") {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  if (typeof window !== "undefined") {
    if (window.location.port === "3000") {
      return "http://127.0.0.1:8000";
    }
    return window.location.origin;
  }
  return "http://127.0.0.1:8000";
};

const API_BASE_URL = getApiBaseUrl();


// Helper component to smoothly center and focus the map on selected features
// It uses Leaflet flyTo to animate view changes instead of hard resetting on every poll update.
function MapController({ selectedNeighborhood, selectedSensor }) {
  const map = useMap();
  
  useEffect(() => {
    if (selectedSensor) {
      map.flyTo([selectedSensor.latitude, selectedSensor.longitude], 14, {
        animate: true,
        duration: 1.2
      });
    } else if (selectedNeighborhood) {
      try {
        const boundary = JSON.parse(selectedNeighborhood.boundary_geojson);
        const originalCoords = boundary.coordinates[0];
        
        // Calculate centroid of the polygon coordinates
        let latSum = 0;
        let lonSum = 0;
        originalCoords.forEach(coord => {
          lonSum += coord[0];
          latSum += coord[1];
        });
        const centerLat = latSum / originalCoords.length;
        const centerLon = lonSum / originalCoords.length;
        
        map.flyTo([centerLat, centerLon], 13, {
          animate: true,
          duration: 1.2
        });
      } catch (e) {
        console.error("Error parsing GeoJSON in MapController flyTo:", e);
      }
    }
  }, [selectedNeighborhood, selectedSensor, map]);

  return null;
}

// Function to return Tailwind-like color for Leaflet elements based on AQI
const getAqiColor = (aqi, status) => {
  if (status === "offline") return "#64748b"; // Slate-500
  if (aqi <= 50) return "#10b981"; // Emerald-500
  if (aqi <= 100) return "#14b8a6"; // Teal-500
  if (aqi <= 200) return "#f59e0b"; // Amber-500
  if (aqi <= 300) return "#f97316"; // Orange-500
  if (aqi <= 400) return "#ef4444"; // Red-500
  return "#d946ef"; // Fuchsia-500
};

export default function SmartCityMap({ 
  neighborhoods, 
  sensors, 
  selectedNeighborhood, 
  selectedSensor, 
  onSelectNeighborhood, 
  onSelectSensor,
  reports = [],
  satelliteData = [],
  activeSatelliteLayer = "none"
}) {
  
  // Centroid of our simulation: India national scale
  const defaultCenter = [20.5937, 78.9629];
  const defaultZoom = 5;

  return (
    <div className="relative w-full h-[550px] rounded-2xl overflow-hidden border border-slate-800 shadow-inner">
      <MapContainer 
        center={defaultCenter} 
        zoom={defaultZoom} 
        scrollWheelZoom={true}
        style={{ width: "100%", height: "100%", background: "#0b1329" }}
      >
        {/* Only trigger dynamic panning/zooming when user clicks a specific card or marker */}
        <MapController selectedNeighborhood={selectedNeighborhood} selectedSensor={selectedSensor} />
        
        {/* Dark Mode CartoDB Tile Layer */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />

        {/* Satellite Overlays */}
        {activeSatelliteLayer !== "none" && satelliteData.map((cell) => {
          let fillColor = "transparent";
          let fillOpacity = 0;
          let color = "transparent";
          let weight = 0;

          if (activeSatelliteLayer === "ndvi") {
            // NDVI: Green scale
            fillColor = "#059669";
            fillOpacity = cell.ndvi * 0.45;
          } else if (activeSatelliteLayer === "urban_density") {
            // Urban Density: Slate grey scale
            fillColor = "#475569";
            fillOpacity = cell.urban_density * 0.55;
          } else if (activeSatelliteLayer === "thermal_anomaly" && cell.thermal_anomaly) {
            // Thermal anomaly: Red bounds and fill
            fillColor = "#dc2626";
            fillOpacity = 0.55;
            color = "#ef4444";
            weight = 1.5;
          }

          if (fillColor === "transparent" && weight === 0) return null;

          return (
            <Polygon
              key={`sat-${cell.id}-${activeSatelliteLayer}`}
              positions={cell.bounds}
              pathOptions={{
                fillColor,
                fillOpacity,
                color,
                weight,
                stroke: weight > 0
              }}
              interactive={activeSatelliteLayer === "thermal_anomaly" && cell.thermal_anomaly}
            >
              {activeSatelliteLayer === "thermal_anomaly" && cell.thermal_anomaly && (
                <Popup>
                  <div className="text-slate-900 font-sans p-1 text-xs">
                    <h3 className="font-bold text-red-600">Satellite Thermal Anomaly</h3>
                    <p>NASA FIRMS Thermal Hotspot flags active fire in the sector grid near {cell.dominant_neighborhood}.</p>
                    <p className="text-[10px] text-slate-500 mt-1">Source: Sentinel-2 Multispectral Index</p>
                  </div>
                </Popup>
              )}
            </Polygon>
          );
        })}

        {/* Neighborhood Polygons */}
        {neighborhoods.map((nb) => {
          try {
            const boundary = JSON.parse(nb.boundary_geojson);
            const originalCoords = boundary.coordinates[0];
            const leafletCoords = originalCoords.map(coord => [coord[1], coord[0]]);
            
            const isSelected = selectedNeighborhood && selectedNeighborhood.name === nb.name;
            const aqiColor = getAqiColor(nb.average_aqi, "active");
            
            return (
              <Polygon
                key={`nb-${nb.id}-${isSelected}-${aqiColor}`}
                positions={leafletCoords}
                pathOptions={{
                  fillColor: aqiColor,
                  fillOpacity: isSelected ? 0.45 : 0.25,
                  color: isSelected ? "#ffffff" : aqiColor,
                  weight: isSelected ? 3 : 1.5,
                  dashArray: isSelected ? "" : "3",
                }}
                eventHandlers={{
                  click: () => {
                    onSelectNeighborhood(nb);
                  },
                  popupopen: () => {
                    onSelectNeighborhood(nb);
                  }
                }}
              >
                <Popup>
                  <div className="text-slate-900 font-sans p-1">
                    <h3 className="font-bold text-base border-b pb-1 mb-1">{nb.name}</h3>
                    <p className="text-sm">Avg AQI: <span className="font-bold">{nb.average_aqi || "N/A"}</span></p>
                    <p className="text-sm">Dominant Pollutant: <span className="font-bold uppercase">{nb.dominant_pollutant}</span></p>
                    <p className="text-sm">Risk Score: <span className="font-bold">{nb.risk_score}/100</span></p>
                    <p className="text-xs text-slate-500 mt-1">Click to view deep analytics</p>
                  </div>
                </Popup>
              </Polygon>
            );
          } catch (e) {
            console.error("Error parsing GeoJSON for neighborhood", nb.name, e);
            return null;
          }
        })}

        {/* Sensor Markers */}
        {sensors.map((sensor) => {
          const aqiColor = getAqiColor(sensor.aqi, sensor.status);
          const isSelected = selectedSensor && selectedSensor.id === sensor.id;
          
          return (
            <CircleMarker
              key={`sensor-${sensor.id}-${isSelected}-${aqiColor}-${sensor.status}`}
              center={[sensor.latitude, sensor.longitude]}
              radius={isSelected ? 9 : 6}
              pathOptions={{
                fillColor: aqiColor,
                fillOpacity: sensor.status === "offline" ? 0.4 : 0.85,
                color: isSelected ? "#ffffff" : "#0f172a",
                weight: isSelected ? 2.5 : 1,
              }}
              eventHandlers={{
                click: () => {
                  onSelectSensor(sensor);
                },
                popupopen: () => {
                  onSelectSensor(sensor);
                }
              }}
            >
              <Popup>
                <div className="text-slate-900 font-sans p-1">
                  <h3 className="font-bold text-sm border-b pb-1 mb-1">{sensor.id} - {sensor.name}</h3>
                  <p className="text-xs">Neighborhood: <span className="font-semibold">{sensor.neighbourhood}</span></p>
                  <p className="text-xs">Status: <span className={`font-semibold capitalize ${sensor.status === 'active' ? 'text-emerald-600' : 'text-slate-500'}`}>{sensor.status}</span></p>
                  {sensor.status === "active" && (
                    <>
                      <p className="text-xs">Current AQI: <span className="font-bold">{sensor.aqi}</span></p>
                      <p className="text-xs">PM2.5: <span className="font-semibold">{sensor.pm25} ug/m³</span></p>
                      <p className="text-xs">PM10: <span className="font-semibold">{sensor.pm10} ug/m³</span></p>
                    </>
                  )}
                  <p className="text-xs">Battery: <span className="font-semibold">{sensor.battery_level}%</span></p>
                  <p className="text-[10px] text-slate-500 mt-1">Last Active: {new Date(sensor.last_active).toLocaleTimeString()}</p>
                </div>
              </Popup>
            </CircleMarker>
          );
        })}

        {/* Citizen Report Markers */}
        {reports.map((report) => (
          <CircleMarker
            key={`report-${report.id}`}
            center={[report.latitude, report.longitude]}
            radius={8}
            pathOptions={{
              fillColor: "#eab308", // Yellow
              fillOpacity: 0.9,
              color: "#ffffff",
              weight: 1.5
            }}
          >
            <Popup>
              <div className="text-slate-900 font-sans p-2 w-[240px]">
                <h3 className="font-bold text-sm border-b pb-1 mb-1.5 flex justify-between items-center">
                  <span>Report #{report.id}</span>
                  <span className="text-[10px] bg-yellow-100 text-yellow-800 px-1.5 py-0.5 rounded font-extrabold uppercase">
                    {report.category}
                  </span>
                </h3>
                {report.photo_url && (
                  <div className="mb-2 rounded overflow-hidden border border-slate-200 aspect-video relative bg-slate-100">
                    <img 
                      src={`${API_BASE_URL}${report.photo_url}`} 
                      alt="Citizen report payload"
                      className="object-cover w-full h-full"
                    />
                  </div>
                )}
                {report.description && (
                  <p className="text-xs text-slate-700 italic mb-1.5 bg-slate-50 p-1.5 rounded border border-slate-100">
                    "{report.description}"
                  </p>
                )}
                <div className="text-[10px] text-slate-500 bg-slate-50 p-1.5 rounded border border-slate-100 space-y-0.5 font-medium">
                  <p className="font-bold text-teal-600 text-[11px] mb-0.5">AI CV Scan Result:</p>
                  <p>Classification: <span className="font-bold">{report.cv_detected_category} ({Math.round((report.cv_confidence || 0) * 100)}%)</span></p>
                  <p>Severity: <span className="font-bold text-red-600">{report.cv_severity}</span></p>
                </div>
                <p className="text-[9px] text-slate-400 mt-2 text-right">
                  {new Date(report.timestamp).toLocaleString()}
                </p>
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
