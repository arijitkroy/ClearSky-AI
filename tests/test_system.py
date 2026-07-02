import sys
import os
import unittest

# Add project root to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import engine, Base, SessionLocal
from backend import models
from ai import cpcb_aqi, cleaner, forecaster, hotspot_detector, explainable_ai, vision_detector, satellite_analyzer


class ClearSkySystemTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_cpcb_aqi_calc(self):
        idx = cpcb_aqi.calculate_sub_index("pm25", 45.0)
        self.assertAlmostEqual(idx, 75.4, places=1)
        
        cat = cpcb_aqi.get_aqi_category(75.4)
        self.assertEqual(cat, "Satisfactory")
        
        readings = {
            "pm25": 45.0,
            "pm10": 80.0,
            "co": 0.5,
            "no2": 25.0
        }
        aqi_val, dominant = cpcb_aqi.calculate_overall_aqi(readings)
        self.assertEqual(dominant, "pm10")
        self.assertGreater(aqi_val, 0)

    def test_02_hotspot_dbscan(self):
        sensor_data = [
            {"id": "SEN-001", "latitude": 28.6100, "longitude": 77.2000, "aqi": 180.0, "neighbourhood": "Downtown", "pm25": 90.0, "pm10": 140.0},
            {"id": "SEN-002", "latitude": 28.6110, "longitude": 77.2010, "aqi": 190.0, "neighbourhood": "Downtown", "pm25": 95.0, "pm10": 150.0},
            {"id": "SEN-003", "latitude": 28.6090, "longitude": 77.1990, "aqi": 175.0, "neighbourhood": "Downtown", "pm25": 88.0, "pm10": 135.0},
            {"id": "SEN-004", "latitude": 28.6900, "longitude": 77.0800, "aqi": 160.0, "neighbourhood": "Suburbs", "pm25": 75.0, "pm10": 120.0},
        ]
        
        hotspots = hotspot_detector.detect_hotspots_dbscan(sensor_data, aqi_threshold=150.0, eps_degrees=0.015, min_samples=2)
        self.assertEqual(len(hotspots), 1)
        self.assertEqual(hotspots[0]["sensor_count"], 3)
        self.assertEqual(hotspots[0]["neighbourhood"], "Downtown")

    def test_03_explainable_ai(self):
        reading = {
            "pm25": 145.0,
            "pm10": 260.0,
            "co": 1.2,
            "no2": 45.0,
            "wind_speed": 0.8,
            "humidity": 85.0,
            "temperature": 25.0
        }
        
        explanation = explainable_ai.explain_hotspot(reading)
        self.assertIn("wind speed", explanation.lower())
        self.assertIn("humidity", explanation.lower())
        
        recs = explainable_ai.generate_recommendations({"aqi": 320.0})
        audiences = [r["target_audience"] for r in recs]
        self.assertIn("Citizen", audiences)
        self.assertIn("Municipality", audiences)

    def test_04_computer_vision_fallback(self):
        """Test CV module fallback behaves gracefully."""
        res = vision_detector.detect_pollution_in_image("nonexistent.jpg", "Smoke")
        self.assertEqual(res["detected_category"], "Smoke")
        self.assertGreater(res["confidence"], 0.5)
        self.assertIn("severity", res)

    def test_05_satellite_analyzer(self):
        """Test satellite grid generator."""
        grids = satellite_analyzer.get_satellite_grids()
        self.assertEqual(len(grids), 100) # 10x10 grid
        self.assertIn("ndvi", grids[0])
        self.assertIn("urban_density", grids[0])

if __name__ == "__main__":
    unittest.main()

