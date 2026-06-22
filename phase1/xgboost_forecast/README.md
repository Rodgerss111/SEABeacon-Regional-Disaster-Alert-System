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
│
├── automation/
│   └── daemon.py          # The 24/7 background process that pings NASA/GDACS
├── api/
│   └── main.py            # FastAPI server to handle DB insertion and routing
├── models/
│   └── seabeacon_xgb_v1.pkl # The serialized 3D XGBoost model artifact
├── src/
│   ├── predict.py         # AI inference logic and vectorization
│   └── train.py           # Pipeline for preprocessing NOAA data and model training
├── .env                   # (Ignored by Git) Contains Supabase credentials
└── requirements.txt       # Core Python dependencies