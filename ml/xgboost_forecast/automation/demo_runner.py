import json
import os
import sys
import time
import subprocess
import uuid
from datetime import datetime, timezone, timedelta

def run_time_lapse_demo():
    print("==================================================")
    print("   SEABeacon Time-Lapse Simulation: Super Typhoon Noru   ")
    print("==================================================\n")
    
    # Paths
    base_dir = os.path.dirname(__file__)
    json_path = os.path.abspath(os.path.join(base_dir, '..', 'src', 'data_pipeline', 'noru_playback.json'))
    live_payload_path = os.path.abspath(os.path.join(base_dir, '..', 'src', 'data_pipeline', 'current_demo_state.json'))
    predict_script = os.path.abspath(os.path.join(base_dir, '..', 'src', 'model', 'predict.py'))

    # Load the static reel
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ [Demo] Could not find playback file at {json_path}")
        sys.exit(1)

    trajectory = data['trajectory']
    total_frames = len(trajectory)
    
    print(f"--> [Demo] Loaded {total_frames} chronological coordinate frames.")
    print("--> [Demo] Launching accelerated 5-second execution loop...\n")
    
    base_time = datetime.now(timezone.utc)
    
    # --- NEW: GENERATE UNIQUE ID FOR LSTM DISTINCTION ---
    run_id = f"demo-run-{uuid.uuid4().hex[:8]}"
    print(f"--> [Demo] Initialized Unique Simulation ID: {run_id}")
    
    # We need a sliding window of 3 to calculate momentum
    for i in range(total_frames - 2):
        print(f"\n🌀 --- DEMO FRAME {i+1} / {total_frames - 2} --- 🌀")
        
        # Slice the 3 necessary points (using copy to avoid mutating the base dict)
        t_12 = trajectory[i].copy()
        t_6 = trajectory[i+1].copy()
        t_0 = trajectory[i+2].copy()
        
        # Inject simulated UTC timestamps so the physics engine doesn't break
        # We step time forward by 6 hours per frame, even though the loop takes 5 seconds
        current_sim_time = base_time + timedelta(hours=(i * 6))
        
        t_12["timestamp"] = (current_sim_time - timedelta(hours=12)).isoformat()
        t_6["timestamp"] = (current_sim_time - timedelta(hours=6)).isoformat()
        t_0["timestamp"] = current_sim_time.isoformat()
        
        # Construct the payload
        payload = {
            "simulation_run_id": run_id,
            "storm_name": data["storm_name"],
            "agency": data["agency"],
            "updates": [t_12, t_6, t_0]
        }
        
        # Write to a temporary file that fetch_realtime.py can intercept
        with open(live_payload_path, 'w') as f:
            json.dump(payload, f)
            
        # Launch the isolated inference engine using sys.executable to maintain .venv
        try:
            subprocess.run([sys.executable, predict_script], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ [Demo] Inference crashed on Frame {i+1}.")
            sys.exit(1)
            
        print("\n--> [Demo] Frame complete. Sleeping 5 seconds before next update...")
        time.sleep(5)
        
    # Clean up the temporary file after the demo finishes
    if os.path.exists(live_payload_path):
        os.remove(live_payload_path)
        
    print("\n✅ [Demo] Time-Lapse Simulation Complete.")

if __name__ == "__main__":
    run_time_lapse_demo()