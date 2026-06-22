# SEABeacon: Phase 1 (Spatial Forecasting Core) 

This directory contains the spatial physics and forecasting engine for the SEABeacon Regional Disaster Alert System. It utilizes an autoregressive XGBoost machine learning pipeline to predict the 72-hour trajectory and intensity of transboundary tropical cyclones in the ASEAN region.

## System Architecture

The forecasting core operates as a 24/7 autonomous daemon designed for cloud deployment:
1. **Ingestion:** Pings the NASA EONET API and GDACS to acquire live, synoptic coordinate drops.
2. **Vectorization:** Converts the raw payload into a 17-feature meteorological tensor (including latitude, longitude, wind speed, pressure, and seasonal sinusoids).
3. **Inference:** Feeds the vector into a pre-trained 3D XGBoost engine.
4. **Autoregression:** Uses a kinematic feedback loop to generate 6, 12, 24, 48, and 72-hour forecast steps, calculating a dynamic Landfall Risk Scope (uncertainty radius) for each step.
5. **Persistence:** Sends the spatial data via a local FastAPI server to a cloud-hosted Supabase PostgreSQL/PostGIS database.

## Model Performance Metrics

The current model artifact (`seabeacon_xgb_v1.pkl`) was trained on NOAA IBTrACS historical cyclone data (1980–present), extracting 30,965 valid multi-dimensional matrices. 

* **Intensity Error (Mean Absolute):** 3.39 knots
* **Spatial Cross-Track Error (Median):** 38.40 km per 6-hour prediction step.

*Note: Because spatial error mathematically compounds during the 72-hour autoregressive loop, the system outputs a dynamic `Landfall Risk Scope` to safely encompass this statistical deviation.*

## 📂 Directory Structure

```text
xgboost_forecast/
├── data/                       # 1. DATA WAREHOUSE (Ignored by Git)
│   ├── raw/                    # Raw IBTrACS CSVs or newly downloaded live data
│   └── shapefiles/             # GADM Philippines, Vietnam, Thailand polygons (.shp, .dbf)
│
├── notebooks/                  # 3. EXPERIMENTATION & SANDBOX
│   ├── 01_exploration.ipynb    # Sandbox for testing
│   └── 02_spatial_migration.ipynb 
│
├── src/                        # 4. CORE ENGINE (The Spatial Physics Pipeline)
│   ├── __init__.py
│   ├── data_pipeline/
│   │   ├── fetch_realtime.py   # Pings GDACS/JTWC API (Supports Live & Historical Replay)
│   │   ├── preprocess.py       # Reusable functions for physics & sliding windows
│   │   └── noru_playback.json  # Trajectory JSON for time-lapse simulation
│   ├── model/
│   │   ├── train.py            # Script to train the XGBoost model and save it
│   │   └── predict.py          # 72-hour Autoregressive Trajectory Loop
│   └── nlp/                    # PHASE 2: SOCIAL MEDIA ENGINE
│       └── simulate_stream.py  # Geofenced Crisis Stream Generator
│
├── automation/                 # 5. 24/7 DAEMON & DEMO LAYER
│   ├── daemon.py               # Hourly scheduler handling deduplication
│   └── demo_runner.py          # Accelerated 5-second 72-hour simulation loop
│
├── api/                        # 6. BACKEND MICROSERVICE
│   └── main.py                 # FastAPI PostGIS API & Supabase Cloud Logger
│
├── integration/                # 7. ENSEMBLE PARTNER SCRIPTS (NEW)
│   └── lstm_fetch_example.py   # Python REST fetcher for LSTM time-series ingestion
│
├── models/                     # 8. SAVED ARTIFACTS
│   └── seabeacon_xgb_v1.pkl    
│
├── .env                        
├── .gitignore                  
├── requirements.txt            
└── README.md         

## ☁️ Cloud & Database Infrastructure

This pipeline is engineered to operate headlessly in the cloud, utilizing a decoupled architecture between compute (Google Cloud) and storage (Supabase).

### 1. Supabase (PostgreSQL + PostGIS)
We utilize Supabase as our remote spatial database. The FastAPI server (`api/main.py`) actively listens for predictions from the AI and executes POST requests to log the 72-hour `Landfall Risk Scope` coordinates into the cloud.

**Setup Instructions:**
1. Create a project in your Supabase dashboard.
2. Ensure you have a table named `seabeacon_forecasts` configured to accept simulation run IDs, latitudes, longitudes, wind speeds, and risk radii.
3. Navigate to **Project Settings > Database > Connection string > URI**.
4. Create a hidden `.env` file in the root of the `xgboost_forecast` directory. Git will ignore this file to protect your credentials.
5. Paste your connection string inside the `.env` file:
   ```env
   DATABASE_URL="postgresql://postgres.[your-project]:[your-password]@[aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres](https://aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres)"

🛠️ How to Use This Directory
Depending on your objective, there are two distinct ways to execute the code in this folder: Local Testing Mode and Cloud Production Mode.

Mode A: Local Testing & Development
Use this mode if you are actively modifying the XGBoost model, tweaking the 17-feature vector logic, or running historical backtests on your local machine.

Navigate to the directory: cd SEABeacon-Regional-Disaster-Alert-System/phase1/xgboost_forecast

Activate your environment:

Windows: .venv\Scripts\activate

Mac/Linux: source .venv/bin/activate

Run a manual test: Execute the demo script to force a prediction run without waiting for the 1-hour daemon sleep cycle.

Bash
python src/demo_runner.py
Mode B: Cloud Production (24/7 Deployment)
Use this mode when SSH'd into your Google Cloud server to start the autonomous pipeline. We must launch both the API and the Ingestion Daemon simultaneously using tmux.

Step 1: Prepare the Cloud Environment

Bash
sudo apt update && sudo apt install python3-venv tmux -y
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
Step 2: Initialize the Master Session
Create a new, persistent background session named seabeacon:

Bash
tmux new -s seabeacon
Step 3: Launch the Storage API (Window 1)
This starts the localized server that routes AI predictions to Supabase.

Bash
source .venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000
Step 4: Launch the Autonomous Daemon (Window 2)
Open a second terminal tab inside the tmux session by pressing Ctrl + B, releasing both keys, and tapping C. Then, start the ingestion loop:

Bash
source .venv/bin/activate
python automation/daemon.py
Step 5: Safely Detach
To leave the server running indefinitely, you must detach from the session without terminating the scripts.

Press Ctrl + B, release both keys, and tap D.

Alternatively, simply close your SSH browser window. The daemon will continue tracking NASA EONET and logging spatial data to Supabase autonomously.

Reattaching: If you ever need to check the live logs or halt the daemon, SSH back into the Google Cloud server and run: tmux attach -t seabeacon