import pandas as pd
from datetime import datetime, timezone
import numpy as np
import requests # Back to standard, reliable requests!

def fetch_active_typhoon_data(live_mode=False):
    if live_mode:
        print("--> [Ingest] Connecting to NASA EONET (Earth Observatory) API...")
        try:
            # NASA's open API for severe storms (Zero Firewalls)
            url = "https://eonet.gsfc.nasa.gov/api/v3/events?category=severeStorms&status=open"
            
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Search NASA's active events for Typhoons or Cyclones
            for event in data.get('events', []):
                title = event.get('title', '').lower()
                
                # We need at least 3 historical points to calculate momentum for your XGBoost
                geometries = event.get('geometry', [])
                
                if ('typhoon' in title or 'cyclone' in title or 'hurricane' in title) and len(geometries) >= 3:
                    storm_name = event.get('title')
                    print(f"--> [Ingest] ✅ NASA Data Acquired: {storm_name}")
                    
                    # Get the most recent 3 track points (t-12, t-6, t0)
                    track = geometries[-3:]
                    updates = []
                    
                    for geo in track:
                        lon, lat = geo['coordinates']
                        # NASA provides wind in knots. Convert to KPH for your engine.
                        wind_kts = geo.get('magnitudeValue') or 50.0 
                        wind_kph = wind_kts * 1.852
                        
                        # Estimate pressure dynamically from wind speed for the ML engine
                        pressure_hpa = 1010 - (wind_kph / 10.0)
                        
                        updates.append({
                            "timestamp": geo['date'],
                            "latitude": lat,
                            "longitude": lon,
                            "wind_kph": round(wind_kph, 2),
                            "pressure_hpa": round(pressure_hpa, 2),
                            "distance_to_land_km": 150.0 # Placeholder assumption for open ocean
                        })
                        
                    api_payload = {
                        "storm_name": storm_name,
                        "agency": "NASA EONET",
                        "updates": updates
                    }
                    
                    # Pass the clean NASA data down to your AI vectorizer
                    return api_payload
            
            print("--> [Ingest] NASA EONET currently shows zero active storms with sufficient tracking data.")
            print("--> [Ingest] Falling back to safe mode simulation...")

        except Exception as e:
            print(f"--> [Ingest] CRITICAL: NASA EONET connection failed ({e}). Falling back to safe mode.")

    # ---------------------------------------------------------
    # FAILSAFE DEMO PAYLOAD (Simulating Super Typhoon Yagi 2024)
    # ---------------------------------------------------------
    current_time = datetime.now(timezone.utc)
    return {
        "storm_name": "Super Typhoon Yagi (Live Simulation)",
        "agency": "JTWC/PAGASA Simulated Feed",
        "updates": [
            {
                "timestamp": (current_time - pd.Timedelta(hours=12)).isoformat(),
                "latitude": 19.10, "longitude": 114.20,
                "wind_kph": 250.0, "pressure_hpa": 915.0,
                "distance_to_land_km": 350.0
            },
            {
                "timestamp": (current_time - pd.Timedelta(hours=6)).isoformat(),
                "latitude": 19.30, "longitude": 112.80,
                "wind_kph": 240.0, "pressure_hpa": 922.0,
                "distance_to_land_km": 150.0
            },
            {
                "timestamp": current_time.isoformat(),
                "latitude": 19.60, "longitude": 111.40, # Approaching Gulf of Tonkin
                "wind_kph": 230.0, "pressure_hpa": 930.0,
                "distance_to_land_km": 50.0
            }
        ]
    }

def vectorize_live_payload(api_payload):
    print("--> [Ingest] Vectorizing live data for XGBoost compatibility...")
    updates = api_payload["updates"]
    t_12, t_6, t_0 = updates[0], updates[1], updates[2]
    
    wind_t12_kt, wind_t6_kt, wind_t0_kt = t_12["wind_kph"]/1.852, t_6["wind_kph"]/1.852, t_0["wind_kph"]/1.852
    delta_lat, delta_lon = t_0["latitude"] - t_6["latitude"], t_0["longitude"] - t_6["longitude"]
    
    current_time = datetime.fromisoformat(t_0["timestamp"])
    day_of_year = current_time.timetuple().tm_yday
    sin_season, cos_season = np.sin(2 * np.pi * day_of_year / 365.25), np.cos(2 * np.pi * day_of_year / 365.25)
    is_over_land = 1 if t_0["distance_to_land_km"] <= 0 else 0
    
    feature_vector = np.array([[
        t_12["latitude"], t_12["longitude"], wind_t12_kt, t_12["pressure_hpa"],
        t_6["latitude"], t_6["longitude"], wind_t6_kt, t_6["pressure_hpa"],
        t_0["latitude"], t_0["longitude"], wind_t0_kt, t_0["pressure_hpa"],
        delta_lat, delta_lon, sin_season, cos_season, is_over_land
    ]])
    return feature_vector, api_payload["storm_name"], current_time