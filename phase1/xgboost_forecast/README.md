# SEABeacon: Phase 1 (Spatial Forecasting Core) 🌪️

This directory contains the spatial physics and forecasting engine for the SEABeacon Regional Disaster Alert System. It utilizes an autoregressive XGBoost machine learning pipeline to predict the 72-hour trajectory and intensity of transboundary tropical cyclones in the ASEAN region.

## 🧠 System Architecture

The forecasting core operates as a 24/7 autonomous daemon designed for cloud deployment:
1. **Ingestion:** Pings the NASA EONET API and GDACS to acquire live, synoptic coordinate drops.
2. **Vectorization:** Converts the raw payload into a 17-feature meteorological tensor (including latitude, longitude, wind speed, pressure, and seasonal sinusoids).
3. **Inference:** Feeds the vector into a pre-trained 3D XGBoost engine.
4. **Autoregression:** Uses a kinematic feedback loop to generate 6, 12, 24, 48, and 72-hour forecast steps, calculating a dynamic Landfall Risk Scope (uncertainty radius) for each step.
5. **Persistence:** Sends the spatial data via a local FastAPI server to a cloud-hosted Supabase PostgreSQL/PostGIS database.

## 📊 Model Performance Metrics

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