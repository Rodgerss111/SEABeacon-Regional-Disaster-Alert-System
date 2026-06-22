import sys
import os
import json
import subprocess
import time
from datetime import datetime
import uuid

# Dynamically add the root directory to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_pipeline.fetch_realtime import fetch_active_typhoon_data

# Paths
STATE_FILE = os.path.join(os.path.dirname(__file__), 'last_state.json')
LIVE_PAYLOAD_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'data_pipeline', 'current_demo_state.json'))

def load_last_state():
    """Loads the timestamp of the last processed storm update."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"last_event_name": None, "last_timestamp": None}

def save_state(name, timestamp):
    """Saves the new timestamp to prevent duplicate XGBoost runs."""
    with open(STATE_FILE, 'w') as f:
        json.dump({"last_event_name": name, "last_timestamp": timestamp}, f)

def run_daemon_loop():
    print("==================================================")
    print("   SEABeacon 24/7 Autonomous Daemon Active        ")
    print("==================================================\n")
    
    # Infinite loop to keep the process running 24/7
    while True:
        current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[🕒 {current_time_str}] Wake up cycle initiated. Pinging GDACS...")
        
        # 1. Fetch LIVE data from GDACS
        raw_data = fetch_active_typhoon_data(live_mode=True)

        # Handle API fallbacks or missing data
        if not raw_data:
            print("--> [Daemon] No active storms detected. Sleeping for 1 hour.")
            time.sleep(3600)
            continue

        storm_name = raw_data["storm_name"]
        latest_update_time = raw_data["updates"][-1]["timestamp"]

        # 2. Check State to prevent duplicate logging
        state = load_last_state()
        last_time = state.get("last_timestamp")

        if latest_update_time == last_time:
            print(f"✅ [Daemon] No new movement detected for {storm_name}. Sleeping for 1 hour.")
            time.sleep(3600)
            continue

        print(f"\n⚠️ [Daemon] NEW STORM UPDATE: {storm_name}")
        print(f"       Latest Coordinates Timestamp: {latest_update_time}")
        
        # 3. Setup Coordinate Logging (Supabase Integration)
        # Create a unique ID for this specific live detection so Supabase tracks it cleanly
        run_id = f"live-production-{uuid.uuid4().hex[:8]}"
        raw_data["simulation_run_id"] = run_id
        
        # Intercept mechanism: write the live data to the state file
        # so predict.py uses the exact payload the daemon just verified
        with open(LIVE_PAYLOAD_PATH, 'w') as f:
            json.dump(raw_data, f)
            
        print(f"--> [Daemon] Generated Live Run ID: {run_id}")
        print("--> [Daemon] Launching AI Inference Engine...")
        
        predict_script = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'model', 'predict.py'))
        
        try:
            # Launch the isolated prediction environment
            subprocess.run([sys.executable, predict_script], check=True)
            
            # Only save state if prediction and database logging succeeded
            save_state(storm_name, latest_update_time)
            print(f"✅ [Daemon] Cycle complete. Live coordinates securely logged to Supabase.")
            
        except subprocess.CalledProcessError as e:
            print(f"\n❌ [Daemon] CRITICAL ERROR: Inference engine crashed. (Exit code: {e.returncode})")
        
        # Cleanup the interception payload
        if os.path.exists(LIVE_PAYLOAD_PATH):
            os.remove(LIVE_PAYLOAD_PATH)
            
        print("--> [Daemon] Entering standby mode for 1 hour...")
        time.sleep(3600)

if __name__ == "__main__":
    run_daemon_loop()