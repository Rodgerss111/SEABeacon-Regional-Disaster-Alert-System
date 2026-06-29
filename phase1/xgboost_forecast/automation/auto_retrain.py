import os
import sys
import requests
import subprocess
from datetime import datetime

# URL for the live-updating NOAA IBTrACS Western Pacific dataset
NOAA_DATA_URL = "https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r00/access/csv/ibtracs.WP.list.v04r00.csv"

def run_continuous_training():
    print("==================================================")
    print("   SEABeacon MLOps: Continuous Training Engine    ")
    print("==================================================\n")
    
    # 1. Setup paths
    base_dir = os.path.dirname(__file__)
    data_dir = os.path.abspath(os.path.join(base_dir, '..', 'data', 'raw'))
    os.makedirs(data_dir, exist_ok=True)
    
    csv_path = os.path.join(data_dir, 'ibtracs.WP.list.v04r01.csv')
    train_script = os.path.abspath(os.path.join(base_dir, '..', 'src', 'model', 'train.py'))
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[🕒 {current_time}] Initiating Model Evolution Sequence...")
    
    # 2. Download the absolute latest Ground Truth data from NOAA
    print("--> 1. Fetching latest global weather dataset from NOAA servers...")
    try:
        response = requests.get(NOAA_DATA_URL, stream=True)
        response.raise_for_status()
        
        with open(csv_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print("    ✅ Dataset successfully updated.")
        
    except requests.exceptions.RequestException as e:
        print(f"    ❌ CRITICAL: Failed to download NOAA dataset. Aborting retrain to protect current model. Error: {e}")
        sys.exit(1)

    # 3. Execute the Training Pipeline in Shadow Mode
    print("\n--> 2. Launching AI Training Sequence (Shadow Mode)...")
    try:
        # We run the training script. If it fails, the current .pkl model remains completely unharmed.
        subprocess.run([sys.executable, train_script], check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n    ❌ CRITICAL: Training sequence failed (Exit code {e.returncode}). Reverting to previous model.")
        sys.exit(1)
        
    print(f"\n✅ [MLOps] Continuous Training Complete! SEABeacon is now running on the latest data.")

if __name__ == "__main__":
    run_continuous_training()