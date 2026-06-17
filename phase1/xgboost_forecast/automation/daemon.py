import sys
import os
import json
import subprocess
from datetime import datetime

# Dynamically add the root directory to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_pipeline.fetch_realtime import fetch_active_typhoon_data

# The local memory file where the daemon tracks what it has already processed
STATE_FILE = os.path.join(os.path.dirname(__file__), 'last_state.json')

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

def run_daemon():
    print("==================================================")
    print("   SEABeacon Autonomous Daemon (Hourly Cron)      ")
    print("==================================================\n")
    
    print("--> [Daemon] 1. Checking previous execution state...")
    state = load_last_state()
    last_time = state.get("last_timestamp")
    print(f"       Last Processed Update: {last_time if last_time else 'None (First Run)'}")

    print("\n--> [Daemon] 2. Pinging API for live meteorological data...")
    # NOTE: For this test, we use the Historical Replay to guarantee data.
    # In full production, you simply change this to: fetch_active_typhoon_data(live_mode=True)
    raw_data = fetch_active_typhoon_data(live_mode=True, replay_event_id=None) #production live mode
    #raw_data = fetch_active_typhoon_data(live_mode=False, replay_event_id="1001082") #historical replay mode (for testing AI / deduplication)

    if not raw_data:
        print("\n--> [Daemon] No active storms detected globally. Safely shutting down.")
        sys.exit(0)

    # Extract current event details
    storm_name = raw_data["storm_name"]
    latest_update_time = raw_data["updates"][-1]["timestamp"]

    print(f"\n--> [Daemon] 3. State Verification...")
    print(f"       Current Target: {storm_name}")
    print(f"       Latest Update:  {latest_update_time}")

    # Deduplication Logic
    if latest_update_time == last_time:
        print("\n✅ [Daemon] Data is identical to the last hourly run. No new trajectory needed.")
        print("--> Safely shutting down to flush memory.")
        sys.exit(0)
    
    print("\n⚠️ [Daemon] NEW METEOROLOGICAL DATA DETECTED.")
    print("--> Updating state tracker...")
    save_state(storm_name, latest_update_time)

    print("--> 4. Launching isolated inference engine (predict.py)...")
    # We use subprocess to run predict.py in a completely separate memory space.
    # When predict.py finishes, its memory is completely wiped by the OS, preventing leaks.
    predict_script = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'model', 'predict.py'))
    
    try:
        # Run the XGBoost script and stream its output directly to this console
        subprocess.run([sys.executable, predict_script], check=True)
        print("\n✅ [Daemon] Hourly cycle complete. Shutting down successfully.")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ [Daemon] CRITICAL ERROR: Inference engine crashed. (Exit code: {e.returncode})")
        sys.exit(1)

if __name__ == "__main__":
    run_daemon()