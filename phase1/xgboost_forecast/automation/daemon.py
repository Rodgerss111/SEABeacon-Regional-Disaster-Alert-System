import sys
import os
import json
import subprocess
import time
from datetime import datetime, timezone
import uuid

# Dynamically add the root directory to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_pipeline.fetch_realtime import fetch_active_typhoon_data

# Paths
STATE_FILE = os.path.join(os.path.dirname(__file__), 'last_state.json')
LIVE_PAYLOAD_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'data_pipeline', 'current_demo_state.json'))

def load_last_state():
    """Loads the dictionary of last processed spatial states for all active storms."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                data = json.load(f)
                # Convert legacy single-storm format to multi-storm dictionary seamlessly
                if "last_timestamp" in data and "last_event_name" in data:
                    name = data.get("last_event_name")
                    ts = data.get("last_timestamp")
                    if name and ts:
                        return {name: ts}
                    return {}
                return data
        except Exception:
            return {}
    return {}

def save_state(name, state_string):
    """Saves the combined Time+Spatial state for a specific storm."""
    states = load_last_state()
    states[name] = state_string
    with open(STATE_FILE, 'w') as f:
        json.dump(states, f, indent=4)

def run_daemon_loop():
    print("==================================================")
    print("   SEABeacon 24/7 Autonomous Daemon Active        ")
    print("==================================================\n")
    
    # Infinite loop to keep the process running 24/7
    while True:
        current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[🕒 {current_time_str}] Wake up cycle initiated. Pinging GDACS...")
        
        try:
            # 1. Fetch LIVE data from GDACS / NASA
            raw_data = fetch_active_typhoon_data(live_mode=True)
        except Exception as e:
            print(f"❌ [Daemon] Network or API failure: {e}. Retrying in 1 hour.")
            time.sleep(3600)
            continue

        # Handle API fallbacks or completely empty responses
        if not raw_data:
            print("--> [Daemon] No active storms detected. Sleeping for 1 hour.")
            time.sleep(3600)
            continue

        # Normalize raw_data to always be an iterable list of storm dictionaries
        if isinstance(raw_data, dict):
            if "storm_name" in raw_data:
                storms_list = [raw_data]
            elif "events" in raw_data:
                storms_list = raw_data["events"]
            else:
                storms_list = [raw_data]
        elif isinstance(raw_data, list):
            storms_list = raw_data
        else:
            storms_list = []

        if not storms_list:
            print("--> [Daemon] Valid storm payload structure empty. Sleeping for 1 hour.")
            time.sleep(3600)
            continue

        print(f"--> [Daemon] Detected {len(storms_list)} active storm target(s) in regional scope.")
        states = load_last_state()

        for storm_data in storms_list:
            try:
                if not isinstance(storm_data, dict):
                    continue

                storm_name = storm_data.get("storm_name")
                updates = storm_data.get("updates", [])

                # Reject incomplete payloads immediately before database contact
                if not storm_name or not updates or not isinstance(updates, list) or len(updates) == 0:
                    print(f"⚠️ [WARNING] Incomplete payload for target. Skipping to prevent NULL database records.")
                    continue

                latest_update = updates[-1]
                
                # ==========================================
                # USER'S FIX: AUTO-TIMESTAMP FAILSAFE
                # ==========================================
                latest_update_time = latest_update.get("timestamp")
                if not latest_update_time:
                    latest_update_time = datetime.now(timezone.utc).isoformat()
                    latest_update["timestamp"] = latest_update_time
                    print(f"    [Failsafe] Missing API timestamp. Auto-injecting collection time: {latest_update_time}")

                # THE BUG FIX: Correctly check for 'latitude' and 'longitude'
                lat = latest_update.get("latitude")
                lon = latest_update.get("longitude")

                if lat is None or lon is None:
                    print(f"⚠️ [WARNING] Missing GPS coordinates for {storm_name}. Skipping.")
                    continue

                # ==========================================
                # NEW SPATIAL STATE CHECKER
                # ==========================================
                # We track the exact GPS coordinates. If the time changes but the storm hasn't moved, we skip.
                current_state_signature = f"{latest_update_time}_{lat}_{lon}"
                last_state_signature = states.get(storm_name)

                if current_state_signature == last_state_signature:
                    print(f"✅ [Daemon] No new spatial movement detected for {storm_name}. Skipping inference.")
                    continue

                print(f"\n⚠️ [Daemon] NEW STORM UPDATE: {storm_name}")
                print(f"        Latest Coordinates: Lat {lat}, Lon {lon}")
                print(f"        Base Timestamp: {latest_update_time}")
                
                # 3. Setup Coordinate Logging (Supabase Integration)
                run_id = f"live-production-{uuid.uuid4().hex[:8]}"
                storm_data["simulation_run_id"] = run_id
                
                # Intercept mechanism: write the live data to the state file
                with open(LIVE_PAYLOAD_PATH, 'w') as f:
                    json.dump(storm_data, f)
                    
                print(f"--> [Daemon] Generated Live Run ID: {run_id}")
                print(f"--> [Daemon] Launching AI Inference Engine for {storm_name}...")
                
                predict_script = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'model', 'predict.py'))
                
                # Launch the isolated prediction environment
                subprocess.run([sys.executable, predict_script], check=True)
                
                # Only save state if prediction and database logging succeeded
                save_state(storm_name, current_state_signature)
                states[storm_name] = current_state_signature
                print(f"✅ [Daemon] Cycle complete for {storm_name}. Live coordinates securely logged to Supabase.")
                
            except subprocess.CalledProcessError as e:
                print(f"\n❌ [Daemon] CRITICAL ERROR: Inference engine crashed for {storm_name}. (Exit code: {e.returncode})")
            except Exception as e:
                print(f"\n❌ [Daemon] Unexpected failure processing {storm_data.get('storm_name', 'unknown')}: {e}")
            finally:
                # Clean up the interception payload before moving to the next storm
                if os.path.exists(LIVE_PAYLOAD_PATH):
                    os.remove(LIVE_PAYLOAD_PATH)
                    
        print("\n--> [Daemon] Standby mode engaged. Sleeping for 1 hour...")
        time.sleep(3600)

if __name__ == "__main__":
    run_daemon_loop()