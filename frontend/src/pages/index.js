import { useState, useEffect } from "react";
import Head from "next/head";
import dynamic from "next/dynamic";
import { 
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area 
} from "recharts";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Activity, AlertTriangle, CloudRain, Shield, Trash2, Cpu, Wind, Info, RefreshCw, Layers, Compass, BatteryCharging, CheckCircle, Navigation, Camera, Upload, AlertOctagon, Eye, Plus, Send 
} from "lucide-react";

// Dynamically load the Leaflet Map component with SSR disabled
const SmartCityMap = dynamic(() => import("../components/Map"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[550px] bg-slate-900 rounded-2xl flex items-center justify-center border border-slate-800 animate-pulse">
      <div className="text-center">
        <Layers className="h-10 w-10 text-teal-500 animate-spin mx-auto mb-2" />
        <p className="text-slate-400 text-sm font-medium">Loading Interactive GIS Map...</p>
      </div>
    </div>
  ),
});

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


export default function Dashboard() {
  const [sensors, setSensors] = useState([]);
  const [neighborhoods, setNeighborhoods] = useState([]);
  const [hotspots, setHotspots] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [analytics, setAnalytics] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [reports, setReports] = useState([]);
  const [satelliteData, setSatelliteData] = useState([]);
  
  const [selectedNeighborhood, setSelectedNeighborhood] = useState(null);
  const [selectedSensor, setSelectedSensor] = useState(null);
  const [forecastData, setForecastData] = useState(null);
  
  const [activeTab, setActiveTab] = useState("overview"); // overview, analytics, comparison
  const [activeSatelliteLayer, setActiveSatelliteLayer] = useState("none"); // none, ndvi, urban_density, thermal_anomaly
  
  const [simulatorStatus, setSimulatorStatus] = useState("normal");
  const [isLoading, setIsLoading] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState("");

  // Citizen Report Form State
  const [showReportForm, setShowReportForm] = useState(false);
  const [reportCategory, setReportCategory] = useState("Smoke");
  const [reportDescription, setReportDescription] = useState("");
  const [reportNb, setReportNb] = useState("Industrial Zone");
  const [reportLat, setReportLat] = useState(28.6500);
  const [reportLon, setReportLon] = useState(77.1200);
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [cvResult, setCvResult] = useState(null);
  const [isSubmittingReport, setIsSubmittingReport] = useState(false);

  // Fetch all live data from backend
  const fetchLiveData = async () => {
    try {
      // Parallel fetches for speed and efficiency
      const [resSensors, resNbs, resHs, resAlerts, resRecs, resAnalytics, resReports, resSat] = await Promise.all([
        fetch(`${API_BASE_URL}/api/sensors`),
        fetch(`${API_BASE_URL}/api/neighborhoods`),
        fetch(`${API_BASE_URL}/api/hotspots`),
        fetch(`${API_BASE_URL}/api/alerts`),
        fetch(`${API_BASE_URL}/api/recommendations`),
        fetch(`${API_BASE_URL}/api/analytics`),
        fetch(`${API_BASE_URL}/api/reports`),
        fetch(`${API_BASE_URL}/api/satellite`)
      ]);

      const dataSensors = await resSensors.json();
      const dataNbs = await resNbs.json();
      const dataHs = await resHs.json();
      const dataAlerts = await resAlerts.json();
      const dataRecs = await resRecs.json();
      const dataAnalytics = await resAnalytics.json();
      const dataReports = await resReports.json();
      const dataSat = await resSat.json();

      setSensors(dataSensors || []);
      setNeighborhoods(dataNbs || []);
      setHotspots(dataHs || []);
      setAlerts(dataAlerts || []);
      setRecommendations(dataRecs || []);
      setAnalytics(dataAnalytics || []);
      setReports(dataReports || []);
      setSatelliteData(dataSat || []);
      
      setLastRefreshed(new Date().toLocaleTimeString());
    } catch (e) {
      console.error("Connection failed with backend", e);
    }
  };

  // Poll data every 4 seconds
  useEffect(() => {
    fetchLiveData();
    const interval = setInterval(fetchLiveData, 4000);
    return () => clearInterval(interval);
  }, []);

  // Fetch forecast whenever selection changes or refresh completes
  useEffect(() => {
    const fetchForecast = async () => {
      if (!selectedNeighborhood && !selectedSensor) {
        setForecastData(null);
        return;
      }
      
      let url = `${API_BASE_URL}/api/forecast?`;
      if (selectedSensor) {
        url += `sensor_id=${selectedSensor.id}`;
      } else if (selectedNeighborhood) {
        url += `neighbourhood=${encodeURIComponent(selectedNeighborhood.name)}`;
      }
      
      try {
        const res = await fetch(url);
        const data = await res.json();
        setForecastData(data);
      } catch (e) {
        console.error("Failed to load forecast metrics", e);
      }
    };
    
    fetchForecast();
  }, [selectedNeighborhood, selectedSensor, lastRefreshed]);

  // Align reporting coordinates when neighborhood changes in form
  const handleFormNbChange = (nbName) => {
    setReportNb(nbName);
    // Center coords for neighborhoods
    const centers = {
      "Industrial Zone": { lat: 28.6500, lon: 77.1200 },
      "Downtown Business District": { lat: 28.6300, lon: 77.2200 },
      "Residential East": { lat: 28.6200, lon: 77.2800 },
      "Green Valley Park": { lat: 28.5800, lon: 77.2100 },
      "Construction Site North": { lat: 28.6900, lon: 77.1800 },
      "Suburbs West": { lat: 28.6100, lon: 77.0800 }
    };
    if (centers[nbName]) {
      setReportLat(centers[nbName].lat);
      setReportLon(centers[nbName].lon);
    }
  };

  // Handle image changes for upload form
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setCvResult(null); // clear old result
    }
  };

  // Submit report form
  const handleReportSubmit = async (e) => {
    e.preventDefault();
    if (!selectedFile) return;
    
    setIsSubmittingReport(true);
    const formData = new FormData();
    formData.append("photo", selectedFile);
    formData.append("latitude", reportLat);
    formData.append("longitude", reportLon);
    formData.append("neighbourhood", reportNb);
    formData.append("category", reportCategory);
    formData.append("description", reportDescription);

    try {
      const res = await fetch(`${API_BASE_URL}/api/report`, {
        method: "POST",
        body: formData
      });
      if (res.ok) {
        const data = await res.json();
        // Extract vision results
        setCvResult({
          detected: data.cv_detected_category,
          confidence: data.cv_confidence,
          severity: data.cv_severity,
          boxes: JSON.parse(data.bounding_boxes || "[]")
        });
        
        // Reset form inputs except preview
        setReportDescription("");
        
        // Refresh live stats
        fetchLiveData();
      }
    } catch (err) {
      console.error("Failed to submit citizen report", err);
    } finally {
      setIsSubmittingReport(false);
    }
  };

  // Handle simulator events control
  const triggerSimulatorEvent = async (event_type, custom_intensity = 1.0) => {
    setIsLoading(true);
    setSimulatorStatus(event_type);
    try {
      const res = await fetch(`${API_BASE_URL}/api/simulator/control`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event_type,
          intensity: custom_intensity,
          target_sensor_id: selectedSensor ? selectedSensor.id : null,
          target_neighbourhood: selectedNeighborhood ? selectedNeighborhood.name : null
        })
      });
      if (res.ok) {
        fetchLiveData();
      }
    } catch (e) {
      console.error("Failed to trigger event", e);
    } finally {
      setIsLoading(false);
    }
  };

  // Calculation of aggregate stats
  const activeSensorsCount = sensors.filter(s => s.status === "active").length;
  const offlineSensorsCount = sensors.filter(s => s.status === "offline").length;
  const citywideAvgAqi = neighborhoods.length > 0 
    ? Math.round(neighborhoods.reduce((acc, curr) => acc + (curr.average_aqi || 0), 0) / neighborhoods.length)
    : 0;

  // Filter citizen reports based on clicked item
  const selectedReports = reports.filter(r => {
    if (selectedSensor && selectedSensor.neighbourhood === r.neighbourhood) return true;
    if (selectedNeighborhood && selectedNeighborhood.name === r.neighbourhood) return true;
    return false;
  });

  const filteredRecommendations = recommendations.filter(rec => {
    if (selectedSensor && selectedSensor.neighbourhood === rec.neighbourhood) return true;
    if (selectedNeighborhood && selectedNeighborhood.name === rec.neighbourhood) return true;
    if (!selectedSensor && !selectedNeighborhood) return true;
    return false;
  });

  const getAqiBadgeStyle = (aqi) => {
    if (aqi <= 50) return "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
    if (aqi <= 100) return "bg-teal-500/10 text-teal-400 border border-teal-500/20";
    if (aqi <= 200) return "bg-amber-500/10 text-amber-400 border border-amber-500/20";
    if (aqi <= 300) return "bg-orange-500/10 text-orange-400 border border-orange-500/20";
    if (aqi <= 400) return "bg-rose-500/10 text-rose-400 border border-rose-500/20";
    return "bg-fuchsia-500/10 text-fuchsia-400 border border-fuchsia-500/20";
  };

  const getAqiCategoryName = (aqi) => {
    if (aqi <= 50) return "Good";
    if (aqi <= 100) return "Satisfactory";
    if (aqi <= 200) return "Moderate";
    if (aqi <= 300) return "Poor";
    if (aqi <= 400) return "Very Poor";
    return "Severe";
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-teal-500 selection:text-slate-950 pb-12">
      <Head>
        <title>ClearSky AI | Urban Neighborhood Air Quality Dashboard</title>
        <meta name="description" content="AI-Powered Multimodal GIS Air Quality Intelligence Platform" />
      </Head>

      {/* Header */}
      <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-md border-b border-slate-900 px-6 py-4 flex flex-col md:flex-row justify-between items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="bg-gradient-to-tr from-teal-500 to-emerald-400 p-2.5 rounded-xl shadow-lg shadow-teal-500/20">
            <Wind className="h-6 w-6 text-slate-950" />
          </div>
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
              ClearSky AI
            </h1>
            <p className="text-xs text-slate-400 font-medium">Urban Neighborhood Air Quality Platform</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* File Citizen Report Button */}
          <button 
            onClick={() => setShowReportForm(true)} 
            className="flex items-center gap-2 bg-gradient-to-r from-yellow-550 to-amber-550 hover:from-yellow-600 hover:to-amber-600 text-slate-950 font-bold px-4.5 py-1.8 rounded-full shadow-lg shadow-yellow-500/10 text-xs transition"
          >
            <Camera className="h-4 w-4" />
            File Citizen Report
          </button>

          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-full px-4 py-1.5 text-xs text-slate-300">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span>Live Stream (5s)</span>
            <span className="text-slate-500">|</span>
            <span className="font-mono text-slate-400">Refreshed: {lastRefreshed || "Connecting..."}</span>
          </div>

          <button 
            onClick={fetchLiveData} 
            className="p-2 hover:bg-slate-900 border border-transparent hover:border-slate-800 rounded-xl transition text-slate-400 hover:text-slate-200"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </header>

      {/* Main Grid */}
      <main className="max-w-7xl mx-auto px-4 md:px-6 mt-6 space-y-6">

        {/* Aggregate KPI Grid */}
        <section className="grid grid-cols-2 lg:grid-cols-6 gap-4">
          <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-4 flex flex-col justify-between">
            <span className="text-xs font-semibold text-slate-400">Citywide Avg AQI</span>
            <div className="mt-3">
              <div className="text-3xl font-extrabold">{citywideAvgAqi}</div>
              <span className={`text-[10px] px-2 py-0.5 rounded-full inline-block mt-1 font-bold ${getAqiBadgeStyle(citywideAvgAqi)}`}>
                {getAqiCategoryName(citywideAvgAqi)}
              </span>
            </div>
          </div>

          <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-4 flex flex-col justify-between">
            <span className="text-xs font-semibold text-slate-400">Active Sensors</span>
            <div className="mt-3">
              <div className="text-3xl font-extrabold text-emerald-400">{activeSensorsCount}</div>
              <span className="text-[10px] text-slate-500">/{activeSensorsCount + offlineSensorsCount} nodes online</span>
            </div>
          </div>

          <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-4 flex flex-col justify-between">
            <span className="text-xs font-semibold text-slate-400">Citizen Reports</span>
            <div className="mt-3">
              <div className="text-3xl font-extrabold text-yellow-400">{reports.length}</div>
              <span className="text-[10px] text-slate-500">AI Computer Vision verified</span>
            </div>
          </div>

          <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-4 flex flex-col justify-between">
            <span className="text-xs font-semibold text-slate-400">Active Hotspots</span>
            <div className="mt-3">
              <div className="text-3xl font-extrabold text-rose-400">{hotspots.length}</div>
              <span className="text-[10px] text-slate-500">DBSCAN cluster spots</span>
            </div>
          </div>

          <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-4 flex flex-col justify-between">
            <span className="text-xs font-semibold text-slate-400">Heat Island Points</span>
            <div className="mt-3">
              <div className="text-3xl font-extrabold text-fuchsia-400">
                {satelliteData.filter(s => s.thermal_anomaly).length}
              </div>
              <span className="text-[10px] text-slate-500">Thermal anomalies</span>
            </div>
          </div>

          <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-4 flex flex-col justify-between">
            <span className="text-xs font-semibold text-slate-400">Active Alerts</span>
            <div className="mt-3">
              <div className="text-3xl font-extrabold text-amber-500">{alerts.length}</div>
              <span className="text-[10px] text-slate-500">Warnings logged</span>
            </div>
          </div>
        </section>

        {/* Live Simulator & Event Injector controls */}
        <section className="bg-slate-900/30 border border-slate-800/80 rounded-2xl p-6">
          <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 border-b border-slate-800 pb-4 mb-4">
            <div>
              <h2 className="text-lg font-bold flex items-center gap-2">
                <Cpu className="h-5 w-5 text-teal-400" />
                IoT Simulator anomaly triggers
              </h2>
              <p className="text-xs text-slate-400">Inject urban anomalies in the background stream to monitor how AI hotspot modules classifies reports.</p>
            </div>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <button 
              onClick={() => triggerSimulatorEvent("rain")}
              className={`flex items-center justify-center gap-2 py-3 px-4 rounded-xl border font-bold text-sm transition-all ${
                simulatorStatus === "rain" ? "bg-sky-650 text-white border-sky-400 shadow-lg" : "bg-slate-900 border-slate-800 text-slate-300"
              }`}
            >
              <CloudRain className="h-4 w-4" /> Heavy Rainfall
            </button>
            <button 
              onClick={() => triggerSimulatorEvent("rush_hour")}
              className={`flex items-center justify-center gap-2 py-3 px-4 rounded-xl border font-bold text-sm transition-all ${
                simulatorStatus === "rush_hour" ? "bg-amber-650 text-white border-amber-400 shadow-lg" : "bg-slate-900 border-slate-800 text-slate-300"
              }`}
            >
              <Navigation className="h-4 w-4" /> Rush Hour Traffic
            </button>
            <button 
              onClick={() => triggerSimulatorEvent("construction")}
              className={`flex items-center justify-center gap-2 py-3 px-4 rounded-xl border font-bold text-sm transition-all ${
                simulatorStatus === "construction" ? "bg-orange-655 text-white border-orange-400 shadow-lg" : "bg-slate-900 border-slate-800 text-slate-300"
              }`}
            >
              <Trash2 className="h-4 w-4" /> Construction Dust
            </button>
            <button 
              onClick={() => triggerSimulatorEvent("failure")}
              className={`flex items-center justify-center gap-2 py-3 px-4 rounded-xl border font-bold text-sm transition-all ${
                simulatorStatus === "failure" ? "bg-rose-650 text-white border-rose-400 shadow-lg" : "bg-slate-900 border-slate-800 text-slate-300"
              }`}
            >
              <AlertTriangle className="h-4 w-4" /> Network Outage
            </button>
            <button 
              onClick={() => triggerSimulatorEvent("normal")}
              className={`flex items-center justify-center gap-2 py-3 px-4 rounded-xl border font-bold text-sm transition-all ${
                simulatorStatus === "normal" ? "bg-teal-600 text-slate-950 border-teal-400 shadow-lg" : "bg-slate-900 border-slate-800 text-slate-300"
              }`}
            >
              <CheckCircle className="h-4 w-4" /> Reset Normal
            </button>
          </div>
        </section>

        {/* GIS Map & Overlay Panels */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          
          <div className="lg:col-span-8 space-y-6">
            <div className="bg-slate-900/40 border border-slate-800/80 rounded-3xl p-6">
              
              {/* GIS Overlay Controls */}
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-4">
                <div>
                  <h2 className="text-lg font-bold">Smart City Interactive Map Layer</h2>
                  <p className="text-xs text-slate-400">Manage standard vectors or load live satellite index metrics.</p>
                </div>
                
                {/* Satellite Overlays Selector */}
                <div className="flex bg-slate-950 rounded-xl p-1 border border-slate-900 text-xs">
                  <button 
                    onClick={() => setActiveSatelliteLayer("none")}
                    className={`py-1.5 px-3 rounded-lg font-bold transition ${activeSatelliteLayer === "none" ? "bg-teal-500 text-slate-950" : "text-slate-400"}`}
                  >
                    Default vectors
                  </button>
                  <button 
                    onClick={() => setActiveSatelliteLayer("ndvi")}
                    className={`py-1.5 px-3 rounded-lg font-bold transition ${activeSatelliteLayer === "ndvi" ? "bg-teal-500 text-slate-950" : "text-slate-400"}`}
                  >
                    NDVI Vegetation
                  </button>
                  <button 
                    onClick={() => setActiveSatelliteLayer("urban_density")}
                    className={`py-1.5 px-3 rounded-lg font-bold transition ${activeSatelliteLayer === "urban_density" ? "bg-teal-500 text-slate-950" : "text-slate-400"}`}
                  >
                    Urban Density
                  </button>
                  <button 
                    onClick={() => setActiveSatelliteLayer("thermal_anomaly")}
                    className={`py-1.5 px-3 rounded-lg font-bold transition ${activeSatelliteLayer === "thermal_anomaly" ? "bg-teal-500 text-slate-950" : "text-slate-400"}`}
                  >
                    FIRMS Heat
                  </button>
                </div>
              </div>

              {/* Map */}
              <SmartCityMap 
                neighborhoods={neighborhoods}
                sensors={sensors}
                selectedNeighborhood={selectedNeighborhood}
                selectedSensor={selectedSensor}
                reports={reports}
                satelliteData={satelliteData}
                activeSatelliteLayer={activeSatelliteLayer}
                onSelectNeighborhood={(nb) => {
                  setSelectedNeighborhood(nb);
                  setSelectedSensor(null);
                }}
                onSelectSensor={(sensor) => {
                  setSelectedSensor(sensor);
                  setSelectedNeighborhood(null);
                }}
              />
            </div>

            {/* Active Hotspots Attributions */}
            <div className="bg-slate-900/40 border border-slate-800/80 rounded-3xl p-6">
              <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
                <Layers className="h-5 w-5 text-rose-400" />
                Active Hotspots & SHAP explanations
              </h2>
              {hotspots.length === 0 ? (
                <div className="border border-slate-800/60 rounded-2xl p-6 text-center text-slate-500 text-sm">
                  No active spatial hotspots flagged. Clean climate conditions reported.
                </div>
              ) : (
                <div className="space-y-4">
                  {hotspots.map((hs) => (
                    <div 
                      key={`hs-${hs.id}`} 
                      className={`border rounded-2xl p-4 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 ${
                        hs.detection_method === "DBSCAN" 
                          ? "bg-rose-500/5 border-rose-500/20" 
                          : hs.detection_method === "CitizenReportCluster"
                            ? "bg-yellow-500/5 border-yellow-500/20"
                            : "bg-fuchsia-500/5 border-fuchsia-500/20"
                      }`}
                    >
                      <div className="space-y-1 max-w-2xl">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-extrabold text-sm text-slate-100">{hs.neighbourhood}</span>
                          <span className={`text-[10px] uppercase tracking-wider font-extrabold px-2 py-0.5 rounded-full ${
                            hs.detection_method === "DBSCAN" 
                              ? "bg-rose-500/10 text-rose-400 border border-rose-500/20" 
                              : hs.detection_method === "CitizenReportCluster"
                                ? "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20"
                                : "bg-fuchsia-500/10 text-fuchsia-400 border border-fuchsia-500/20"
                          }`}>
                            {hs.detection_method}
                          </span>
                          <span className="text-xs text-slate-400">Confidence: {Math.round(hs.confidence * 100)}%</span>
                        </div>
                        <p className="text-xs text-slate-400 italic">
                          Main pollutant drivers: <span className="font-semibold uppercase text-slate-300">{hs.main_pollutants}</span>
                        </p>
                        <p className="text-xs text-slate-300 leading-relaxed font-medium bg-slate-950/40 p-2.5 rounded-xl border border-slate-900 mt-2">
                          <span className="font-bold text-teal-400 flex items-center gap-1.5 mb-0.5">
                            <Info className="h-3.5 w-3.5" /> Attribution Explanation:
                          </span>
                          {hs.explanation}
                        </p>
                      </div>
                      
                      <div className="text-right">
                        <span className="text-[10px] text-slate-500 block">Logged</span>
                        <span className="text-xs font-mono text-slate-400">
                          {new Date(hs.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Details Sidebar Panel */}
          <div className="lg:col-span-4 space-y-6">
            <AnimatePresence mode="wait">
              {(!selectedNeighborhood && !selectedSensor) ? (
                <motion.div 
                  key="no-selection"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="bg-slate-900/40 border border-slate-800/80 rounded-3xl p-6 text-center py-12 flex flex-col items-center justify-center animate-pulse"
                >
                  <Compass className="h-12 w-12 text-slate-600 mb-4 stroke-1" />
                  <h3 className="font-bold text-base text-slate-300">No Vector Selected</h3>
                  <p className="text-xs text-slate-500 mt-2 max-w-[240px] leading-relaxed">
                    Click any neighborhood sector boundary or sensor circular marker to load real-time predictions and citizen uploads.
                  </p>
                </motion.div>
              ) : (
                <motion.div 
                  key="selection-details"
                  initial={{ opacity: 0, scale: 0.98 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.98 }}
                  className="bg-slate-900/40 border border-slate-800/80 rounded-3xl p-6 space-y-6"
                >
                  <div>
                    <span className="text-[10px] font-bold text-teal-400 uppercase tracking-widest block">
                      {selectedSensor ? "Sensor Node Details" : "Neighborhood Boundary"}
                    </span>
                    <h3 className="text-lg font-black text-white truncate">
                      {selectedSensor ? `${selectedSensor.id} - ${selectedSensor.name}` : selectedNeighborhood.name}
                    </h3>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        getAqiBadgeStyle(selectedSensor ? selectedSensor.aqi : selectedNeighborhood.average_aqi)
                      }`}>
                        AQI {selectedSensor ? selectedSensor.aqi : selectedNeighborhood.average_aqi} - {getAqiCategoryName(selectedSensor ? selectedSensor.aqi : selectedNeighborhood.average_aqi)}
                      </span>
                    </div>
                  </div>

                  {/* Citizen uploads within sector */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-extrabold uppercase text-slate-400 tracking-wider flex items-center gap-1.5">
                      <Camera className="h-4 w-4 text-yellow-400" />
                      Citizen Photo Uploads
                    </h4>
                    
                    {selectedReports.length === 0 ? (
                      <p className="text-xs text-slate-500">No citizen photos reported in this neighborhood.</p>
                    ) : (
                      <div className="grid grid-cols-3 gap-2 max-h-[120px] overflow-y-auto pr-1">
                        {selectedReports.map((rep) => (
                          <div 
                            key={`rep-thumb-${rep.id}`}
                            className="aspect-square bg-slate-950 border border-slate-900 rounded-lg overflow-hidden relative group cursor-pointer"
                            title={`Report Category: ${rep.category}`}
                          >
                            <img 
                              src={`${API_BASE_URL}${rep.photo_url}`} 
                              alt="Citizen report thumbnail"
                              className="object-cover w-full h-full group-hover:scale-105 transition"
                            />
                            <div className="absolute inset-0 bg-slate-950/60 opacity-0 group-hover:opacity-100 flex items-center justify-center transition">
                              <Eye className="h-4 w-4 text-teal-400" />
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Decision Support recommendations */}
                  <div className="space-y-3 pt-2 border-t border-slate-800/80">
                    <h4 className="text-xs font-extrabold uppercase text-slate-400 tracking-wider flex items-center gap-1">
                      <Shield className="h-4 w-4 text-emerald-400" />
                      Action Center Recommendations
                    </h4>
                    <div className="space-y-2 max-h-[140px] overflow-y-auto pr-1">
                      {filteredRecommendations.map((rec) => (
                        <div 
                          key={`rec-${rec.id}`} 
                          className={`p-2.5 rounded-xl text-xs border ${
                            rec.target_audience === "Citizen" 
                              ? "bg-slate-950/40 border-slate-900 text-slate-300" 
                              : "bg-teal-500/5 border-teal-500/20 text-teal-300"
                          }`}
                        >
                          <span className="font-extrabold uppercase text-[9px] block text-slate-500 mb-0.5">
                            {rec.target_audience}
                          </span>
                          {rec.message}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Predictions compare */}
                  <div className="space-y-3 pt-2 border-t border-slate-800/80">
                    <h4 className="text-xs font-extrabold uppercase text-slate-400 tracking-wider flex items-center gap-1.5">
                      <Cpu className="h-4 w-4 text-teal-400" />
                      XGBoost vs LSTM 24h Predictions
                    </h4>
                    
                    {forecastData ? (
                      <div className="space-y-3">
                        <div className="bg-slate-950/40 rounded-2xl border border-slate-900 overflow-hidden">
                          <table className="w-full text-left border-collapse text-xs">
                            <thead>
                              <tr className="bg-slate-900/60 border-b border-slate-850 text-slate-400 font-bold">
                                <th className="p-2">Horizon</th>
                                <th className="p-2 text-center">XGBoost (AQI)</th>
                                <th className="p-2 text-center">LSTM (AQI)</th>
                              </tr>
                            </thead>
                            <tbody>
                              {Object.entries(forecastData.predictions).map(([horizon, models]) => (
                                <tr key={horizon} className="border-b border-slate-850/50 text-slate-300">
                                  <td className="p-2 font-semibold font-mono text-teal-400">+{horizon}</td>
                                  <td className="p-2 text-center font-bold">{models.xgboost}</td>
                                  <td className="p-2 text-center font-bold">{models.lstm}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    ) : (
                      <div className="text-xs text-slate-500 flex items-center gap-1.5">
                        <RefreshCw className="h-3 w-3 animate-spin" /> Querying ML weights...
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Alert Logs */}
            <div className="bg-slate-900/40 border border-slate-800/80 rounded-3xl p-6 space-y-4">
              <h2 className="text-sm font-extrabold uppercase tracking-widest text-slate-400 flex items-center gap-1.5">
                <AlertTriangle className="h-4.5 w-4.5 text-amber-500" />
                Live Alerts History Log
              </h2>
              <div className="space-y-2.5 max-h-[160px] overflow-y-auto pr-1">
                {alerts.map((al) => (
                  <div 
                    key={`alert-${al.id}`} 
                    className={`p-3 rounded-xl border flex gap-2 items-start text-xs ${
                      al.alert_type === "CLUSTERED_REPORTS"
                        ? "bg-rose-500/10 border-rose-500/30 text-rose-300 animate-pulse"
                        : al.alert_type === "SENSOR_FAILURE" 
                          ? "bg-slate-950/40 border-slate-900 text-slate-400" 
                          : "bg-amber-500/5 border-amber-500/20 text-amber-300"
                    }`}
                  >
                    <AlertOctagon className="h-4 w-4 shrink-0 mt-0.5" />
                    <div>
                      <div className="font-bold flex items-center gap-1.5">
                        <span className="uppercase text-[9px] text-slate-500">{al.alert_type}</span>
                        <span className="text-[10px] text-slate-600 font-mono">| {al.neighbourhood}</span>
                      </div>
                      <p className="mt-0.5 leading-relaxed">{al.message}</p>
                      <span className="text-[9px] text-slate-600 block mt-1 font-mono">
                        {new Date(al.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>

        </section>

        {/* Analytics Charts */}
        <section className="bg-slate-900/40 border border-slate-800/80 rounded-3xl p-6 space-y-6">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-800 pb-4">
            <div>
              <h2 className="text-lg font-bold">24-hour Historical Aggregations</h2>
              <p className="text-xs text-slate-400">Aggregations from virtual IoT nodes.</p>
            </div>
            
            <div className="flex bg-slate-950 rounded-xl p-1 border border-slate-900 text-xs">
              <button 
                onClick={() => setActiveTab("overview")} 
                className={`py-1.5 px-4 rounded-lg font-bold transition ${activeTab === "overview" ? "bg-teal-500 text-slate-950" : "text-slate-400"}`}
              >
                Particulate Matter
              </button>
              <button 
                onClick={() => setActiveTab("analytics")} 
                className={`py-1.5 px-4 rounded-lg font-bold transition ${activeTab === "analytics" ? "bg-teal-500 text-slate-950" : "text-slate-400"}`}
              >
                Gaseous Emissions
              </button>
              <button 
                onClick={() => setActiveTab("comparison")} 
                className={`py-1.5 px-4 rounded-lg font-bold transition ${activeTab === "comparison" ? "bg-teal-500 text-slate-950" : "text-slate-400"}`}
              >
                AQI Area
              </button>
            </div>
          </div>

          <div className="w-full h-[320px] bg-slate-950/40 p-4 rounded-2xl border border-slate-900">
            {analytics.length === 0 ? (
              <div className="w-full h-full flex items-center justify-center text-slate-600 text-sm">
                No historical analytics recorded.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                {activeTab === "overview" ? (
                  <LineChart data={analytics}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="time" stroke="#64748b" style={{ fontSize: 10 }} />
                    <YAxis stroke="#64748b" style={{ fontSize: 10 }} />
                    <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #1e293b' }} />
                    <Legend />
                    <Line type="monotone" dataKey="pm25" stroke="#2dd4bf" strokeWidth={2.5} name="PM2.5" />
                    <Line type="monotone" dataKey="pm10" stroke="#fb923c" strokeWidth={2} name="PM10" />
                  </LineChart>
                ) : activeTab === "analytics" ? (
                  <BarChart data={analytics}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="time" stroke="#64748b" style={{ fontSize: 10 }} />
                    <YAxis stroke="#64748b" style={{ fontSize: 10 }} />
                    <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #1e293b' }} />
                    <Legend />
                    <Bar dataKey="no2" fill="#c084fc" name="NO2" />
                    <Bar dataKey="so2" fill="#f43f5e" name="SO2" />
                    <Bar dataKey="co" fill="#38bdf8" name="CO" />
                  </BarChart>
                ) : (
                  <AreaChart data={analytics}>
                    <defs>
                      <linearGradient id="colorAqi" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#2dd4bf" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#2dd4bf" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="time" stroke="#64748b" style={{ fontSize: 10 }} />
                    <YAxis stroke="#64748b" style={{ fontSize: 10 }} />
                    <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #1e293b' }} />
                    <Legend />
                    <Area type="monotone" dataKey="aqi" stroke="#2dd4bf" fillOpacity={1} fill="url(#colorAqi)" name="AQI Index" strokeWidth={2.5} />
                  </AreaChart>
                )}
              </ResponsiveContainer>
            )}
          </div>
        </section>

      </main>

      {/* Citizen Report Modal Overlay */}
      <AnimatePresence>
        {showReportForm && (
          <div className="fixed inset-0 z-[1000] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
            <motion.div 
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-slate-900 border border-slate-800 rounded-3xl p-6 w-full max-w-xl max-h-[90vh] overflow-y-auto relative shadow-2xl"
            >
              <button 
                onClick={() => { setShowReportForm(false); setPreviewUrl(null); setSelectedFile(null); setCvResult(null); }}
                className="absolute top-4 right-4 text-slate-400 hover:text-white font-black"
              >
                ✕
              </button>
              
              <h3 className="text-lg font-bold flex items-center gap-2 mb-4">
                <Camera className="h-5 w-5 text-yellow-400" />
                Submit Neighborhood Pollution Report
              </h3>
              
              <form onSubmit={handleReportSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-slate-400 font-bold block mb-1">Neighborhood</label>
                    <select 
                      value={reportNb} 
                      onChange={(e) => handleFormNbChange(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs focus:border-teal-500 outline-none text-slate-200"
                    >
                      <option value="Industrial Zone">Industrial Zone</option>
                      <option value="Downtown Business District">Downtown Business District</option>
                      <option value="Residential East">Residential East</option>
                      <option value="Green Valley Park">Green Valley Park</option>
                      <option value="Construction Site North">Construction Site North</option>
                      <option value="Suburbs West">Suburbs West</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 font-bold block mb-1">Report Category</label>
                    <select 
                      value={reportCategory} 
                      onChange={(e) => setReportCategory(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs focus:border-teal-500 outline-none text-slate-200"
                    >
                      <option value="Smoke">Smoke</option>
                      <option value="Construction Dust">Construction Dust</option>
                      <option value="Waste Burning">Waste Burning</option>
                      <option value="Industrial Emissions">Industrial Emissions</option>
                      <option value="Vehicle Pollution">Vehicle Pollution</option>
                      <option value="Garbage Dump">Garbage Dump</option>
                      <option value="Other">Other</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-slate-400 font-bold block mb-1">GPS Latitude</label>
                    <input 
                      type="number" step="0.0001" 
                      value={reportLat} 
                      onChange={(e) => setReportLat(parseFloat(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200" 
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 font-bold block mb-1">GPS Longitude</label>
                    <input 
                      type="number" step="0.0001" 
                      value={reportLon} 
                      onChange={(e) => setReportLon(parseFloat(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200" 
                    />
                  </div>
                </div>

                <div>
                  <label className="text-xs text-slate-400 font-bold block mb-1">Description (Optional)</label>
                  <textarea 
                    value={reportDescription}
                    onChange={(e) => setReportDescription(e.target.value)}
                    placeholder="Enter details of emission triggers..."
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 h-16 outline-none resize-none"
                  />
                </div>

                {/* File picker */}
                <div className="border border-dashed border-slate-800 hover:border-slate-700 bg-slate-950/40 rounded-2xl p-4 text-center cursor-pointer transition relative">
                  <input 
                    type="file" accept="image/*" 
                    onChange={handleFileChange} 
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  />
                  <Upload className="h-6 w-6 text-teal-400 mx-auto mb-1.5" />
                  <span className="text-xs font-bold text-slate-300 block">Choose pollution photo to upload</span>
                  <span className="text-[10px] text-slate-500">Supports PNG, JPG, WEBP (Max 5MB)</span>
                </div>

                {/* Image & CV Result Displays */}
                {previewUrl && (
                  <div className="grid grid-cols-2 gap-4 bg-slate-950/60 p-3 rounded-2xl border border-slate-800/80 items-center">
                    <div className="aspect-video w-full rounded-xl overflow-hidden relative bg-slate-900 border border-slate-850">
                      <img src={previewUrl} className="object-cover w-full h-full" alt="Upload preview" />
                      
                      {/* CV Bounding Box Overlay if exists */}
                      {cvResult && cvResult.boxes.map((box, bIdx) => (
                        <div 
                          key={`box-${bIdx}`}
                          className="absolute border border-red-500 bg-red-500/10 flex items-start"
                          style={{
                            left: `${box.x * 100}%`,
                            top: `${box.y * 100}%`,
                            width: `${box.width * 100}%`,
                            height: `${box.height * 100}%`,
                          }}
                        >
                          <span className="text-[7px] font-bold bg-red-500 text-white px-0.5 leading-none">
                            {box.label}
                          </span>
                        </div>
                      ))}
                    </div>

                    <div className="space-y-1">
                      <span className="text-[9px] uppercase font-bold text-slate-500 block">AI Computer Vision Scan</span>
                      {isSubmittingReport ? (
                        <div className="text-xs text-teal-400 animate-pulse flex items-center gap-1 font-bold">
                          <RefreshCw className="h-3 w-3 animate-spin" /> Classifying pixels...
                        </div>
                      ) : cvResult ? (
                        <div className="space-y-1 text-xs">
                          <p>Object: <span className="font-bold text-slate-200">{cvResult.detected}</span></p>
                          <p>Confidence: <span className="font-bold text-teal-400">{Math.round(cvResult.confidence * 100)}%</span></p>
                          <p>Severity: <span className="font-bold text-red-400">{cvResult.severity}</span></p>
                          {cvResult.boxes.length > 0 && (
                            <p className="text-[10px] text-slate-500 italic">OpenCV detected {cvResult.boxes.length} bounding box contours.</p>
                          )}
                        </div>
                      ) : (
                        <span className="text-[10px] text-slate-500 block">Click submit to analyze image and generate boxes.</span>
                      )}
                    </div>
                  </div>
                )}

                <button 
                  type="submit"
                  disabled={isSubmittingReport || !selectedFile}
                  className="w-full bg-teal-500 text-slate-950 font-black text-xs py-3 rounded-xl hover:bg-teal-400 transition flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Send className="h-4 w-4" />
                  Submit Report to Authorities
                </button>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

    </div>
  );
}
