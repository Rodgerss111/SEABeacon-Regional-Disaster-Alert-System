import os
import requests
import json

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

# Supabase project ref comes from .env (falls back to the AI2 forecast project)
PROJECT_REF = os.getenv("SUPABASE_PROJECT_REF", "axigjjehzqghflrvewaj")

def get_latest_simulation_id(supabase_anon_key):
    """
    Automatically queries the Supabase database to find the 
    simulation_run_id of the most recently inserted forecast.
    """
    TABLE_NAME = "seabeacon_forecasts"
    url = f"https://{PROJECT_REF}.supabase.co/rest/v1/{TABLE_NAME}"
    
    # We ask Supabase for just 1 row, sorted by the newest created_at time
    params = {
        "select": "simulation_run_id",
        "order": "created_at.desc",
        "limit": 1
    }
    
    headers = {
        "apikey": supabase_anon_key,
        "Authorization": f"Bearer {supabase_anon_key}",
        "Content-Type": "application/json"
    }
    
    print("--> Querying Supabase for the latest Simulation Run ID...")
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.json()
        if data:
            latest_id = data[0]["simulation_run_id"]
            print(f"✅ Auto-detected latest run: {latest_id}\n")
            return latest_id
        else:
            print("❌ Database is currently empty.")
            return None
    else:
        print(f"❌ Failed to fetch latest ID. Error {response.status_code}: {response.text}")
        return None

def fetch_xgboost_forecasts(simulation_run_id, supabase_anon_key):
    """
    Fetches the XGBoost predictions from the SEABeacon Supabase API.
    Filters the output to return ONLY the JSON data required by the LSTM:
    - Target Timestamp
    - Latitude
    - Longitude
    - Wind Speed (KPH)
    - Storm Name
    - Warning Scope (km)
    - Alert Status
    - Impact Matrix
    - Base Timestamp        (NEW)
    - Lead Time Hours       (NEW)
    """
    
    TABLE_NAME = "seabeacon_forecasts"
    
    # THE FIX: Added base_timestamp and lead_time_hours to the Supabase SQL query
    columns_needed = "forecast_target_time,predicted_lat,predicted_lon,predicted_wind_kph,storm_name,warning_scope_km,alert_status,impact_matrix,base_timestamp,lead_time_hours"
    
    url = f"https://{PROJECT_REF}.supabase.co/rest/v1/{TABLE_NAME}"
    params = {
        "select": columns_needed,
        "simulation_run_id": f"eq.{simulation_run_id}", 
        "order": "forecast_target_time.asc"             
    }
    
    headers = {
        "apikey": supabase_anon_key,
        "Authorization": f"Bearer {supabase_anon_key}",
        "Content-Type": "application/json"
    }
    
    print(f"--> Pinging SEABeacon Cloud API for Run ID: {simulation_run_id}...")
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Successfully fetched {len(data)} forecast nodes.\n")
        print(json.dumps(data, indent=4))
        return data
    else:
        print(f"❌ API Error {response.status_code}: {response.text}")
        return None

if __name__ == "__main__":
    # --- INSTRUCTIONS FOR LSTM ENGINEER ---
    # 1. The 'anon public' key is read from .env (SUPABASE_ANON_KEY). See .env.example.
    YOUR_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]

    # 2. AUTO-FETCH THE LATEST RUN (No manual ID required!)
    TARGET_RUN_ID = get_latest_simulation_id(YOUR_ANON_KEY) 
    
    # 3. Fetch the JSON data into the LSTM pipeline
    if TARGET_RUN_ID:
        lstm_training_json = fetch_xgboost_forecasts(TARGET_RUN_ID, YOUR_ANON_KEY)