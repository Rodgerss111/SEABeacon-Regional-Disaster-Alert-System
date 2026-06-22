import sys
import os
import requests
import joblib
import numpy as np
import datetime
import json

# Dynamically add the src directory to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Import the Live Data Ingestion Module
from src.data_pipeline.fetch_realtime import fetch_active_typhoon_data, vectorize_live_payload

# Configuration
API_URL = "http://localhost:8000/api/v1/spatial-conversion"
MODEL_PATH = os.path.join('models', 'seabeacon_xgb_v1.pkl')
MEDIAN_ERROR_6H = 38.40  # Sourced directly from your recent training metrics

forecast_intervals = {
    1: "6-Hour Forecast", 2: "12-Hour Forecast",
    4: "24-Hour Forecast", 8: "48-Hour Forecast", 12: "72-Hour Forecast"
}
max_steps = max(forecast_intervals.keys())

def calculate_pressure_from_wind(wind_knots):
    """
    Reverse Atkinson-Holliday conversion. 
    Because the AI predicts wind, we must calculate the corresponding pressure 
    drop to fill the array for the next step of the loop.
    """
    v_1min = wind_knots * 1.14
    if v_1min < 15:
        return 1010.0
    return 1010 - (v_1min / 6.7) ** (1 / 0.644)

def simulate_live_inference():
    print("==================================================")
    print("   SEABeacon Live Inference & API Broadcast       ")
    print("==================================================\n")

    print("--> 1. Loading 3D XGBoost Artifact...")
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Model not found at {MODEL_PATH}. Please run train.py first.")
        return
    model = joblib.load(MODEL_PATH)
    
    print("--> 2. Triggering Live Data Ingest Pipeline...")
    
    # --- THE FIX: INTERCEPT THE DAEMON PAYLOAD ---
    live_payload_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data_pipeline', 'current_demo_state.json'))
    
    if os.path.exists(live_payload_path):
        with open(live_payload_path, 'r') as f:
            raw_api_data = json.load(f)
        print("--> [Predict] Successfully loaded live payload intercepted from Daemon.")
    else:
        print("--> [Predict] No Daemon payload found. Defaulting to safe mode simulation...")
        raw_api_data = fetch_active_typhoon_data(live_mode=False)
        
    current_ml_vector, storm_name, current_time = vectorize_live_payload(raw_api_data)
    
    # Extract the Simulation ID for Supabase logging
    simulation_run_id = raw_api_data.get("simulation_run_id", "live-run-001")
    
    print(f"\n--> 3. Target Locked: {storm_name}")
    # Extracting the current coordinates (index 8 and 9 in our 17-feature array)
    print(f"       Current Position: Lat {current_ml_vector[0][8]:.2f}, Lon {current_ml_vector[0][9]:.2f}")
    print(f"       Current Wind:     {current_ml_vector[0][10]:.2f} knots")
    print(f"       Base Time (UTC):  {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
    
    print("--> 4. Launching 72-Hour Autoregressive AI Loop...\n")
    
    for step in range(1, max_steps + 1):
        
        # 1. Ask XGBoost to predict the future!
        predictions = model.predict(current_ml_vector)
        next_lat, next_lon, next_wind_kt = predictions[0]
        
        # 2. Increment the Metadata Timestamp (FIXED: explicit datetime.timedelta)
        forecast_time = current_time + datetime.timedelta(hours=6 * step)
        
        # ---------------------------------------------------------
        # 3. CALCULATE DYNAMIC LANDFALL RISK SCOPE
        # ---------------------------------------------------------
        # A. Forecast Uncertainty: AI error grows over time (sqrt of steps)
        # Using a baseline median error of ~25km per 6-hour step
        MEDIAN_ERROR_6H = 25.0 
        uncertainty_radius = MEDIAN_ERROR_6H * np.sqrt(step)
        
        # B. Physical Storm Size: Radius scales with AI's predicted wind intensity
        # Heuristic: Base radius of 50km + 1.5km expansion per knot of wind speed
        physical_wind_radius = 50.0 + (next_wind_kt * 1.5)
        
        # C. Total Warning Scope (The true transboundary danger zone)
        total_warning_scope_km = uncertainty_radius + physical_wind_radius
        
        # ---------------------------------------------------------
        # 4. BROADCAST TO FASTAPI & TERMINAL
        # ---------------------------------------------------------
        if step in forecast_intervals:
            horizon_name = forecast_intervals[step]
            wind_speed_kph = round(next_wind_kt * 1.852, 2)
            
            # --- REVERTED TO STANDARD UTC WITH LOCAL TIME APPENDED ---
            utc_str = forecast_time.strftime('%m-%d %H:%M UTC')
            pht_str = (forecast_time + datetime.timedelta(hours=8)).strftime('%I:%M %p')
            ict_str = (forecast_time + datetime.timedelta(hours=7)).strftime('%I:%M %p')
            
            # Print the standard UTC header alongside localized times
            print(f"[{horizon_name} | {utc_str} (PH: {pht_str}, VN/TH: {ict_str})]")
            
            # Print the Spatial Data and the new Dynamic Scope
            print(f"    📍 Predicted Position: Lat {next_lat:.2f}, Lon {next_lon:.2f}")
            print(f"    📏 Landfall Risk Scope: {total_warning_scope_km:.1f} km radius")
            
            # Map the new dynamic scope to the cross_track_error_km payload
            payload = {
                "simulation_run_id": simulation_run_id,
                "storm_name": storm_name,
                "base_timestamp": current_time.isoformat().replace("+00:00", "Z"), # When the forecast was made
                "lead_time_hours": step * 6,                                       # The forecast horizon (6, 12, etc.)
                "timestamp": forecast_time.isoformat().replace("+00:00", "Z"), 
                "latitude": float(round(next_lat, 4)),
                "longitude": float(round(next_lon, 4)),
                "cross_track_error_km": float(round(total_warning_scope_km, 2)),
                "wind_speed_kph": float(wind_speed_kph)
            }
            
            try:
                response = requests.post(API_URL, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    if data['impacted_count'] > 0:
                        print(f"    🚨 THREAT LEVEL: {data['alert_status']} ({wind_speed_kph} KPH)")
                        print("    --- Impact Confidence Matrix ---")
                        for region in data['impacted_regions']:
                            print(f"    * {region['country']} ({region['province']}): {region['confidence_score']}% Confidence")
                    else:
                        print(f"    ✅ {data['alert_status']} | Target safely over ocean.")
                else:
                    print(f"    ❌ API Error {response.status_code}: {response.text}")
            except requests.exceptions.ConnectionError:
                print("    ❌ Connection Refused. Ensure api/main.py is actively running.")
                break
            print("-" * 60)

        # -----------------------------------------------------------------
        # SLIDE THE WINDOW: Update the ML Vector for the next loop (t -> t+6)
        # -----------------------------------------------------------------
        # Extract the old data before we overwrite it
        old_t6_lat, old_t6_lon, old_t6_wind, old_t6_pres = current_ml_vector[0][4:8]
        old_t0_lat, old_t0_lon, old_t0_wind, old_t0_pres = current_ml_vector[0][8:12]
        
        # Calculate dynamic physics for the newly predicted coordinates
        next_pres = calculate_pressure_from_wind(next_wind_kt)
        new_delta_lat = next_lat - old_t0_lat
        new_delta_lon = next_lon - old_t0_lon
        
        day_of_year = forecast_time.timetuple().tm_yday
        new_sin = np.sin(2 * np.pi * day_of_year / 365.25)
        new_cos = np.cos(2 * np.pi * day_of_year / 365.25)
        
        # Assuming the storm is over the ocean for this autoregressive simulation
        new_is_over_land = 0 
        
        # Rebuild the exact 17-feature array, shifting everything backwards
        current_ml_vector = np.array([[
            old_t6_lat, old_t6_lon, old_t6_wind, old_t6_pres,       # The old t-6 becomes the new t-12
            old_t0_lat, old_t0_lon, old_t0_wind, old_t0_pres,       # The old t=0 becomes the new t-6
            next_lat, next_lon, next_wind_kt, next_pres,            # The AI's prediction becomes the new t=0
            new_delta_lat, new_delta_lon, new_sin, new_cos, new_is_over_land
        ]])

    print("\n✅ Full 72-Hour Inference Pipeline Complete.")

if __name__ == "__main__":
    simulate_live_inference()