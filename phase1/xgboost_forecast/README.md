# SEABeacon — Phase 1: Spatial Forecasting Core

> **Autoregressive XGBoost pipeline for 72-hour tropical cyclone trajectory and intensity forecasting across the ASEAN region.**

---

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Model Performance](#model-performance)
4. [Directory Structure](#directory-structure)
5. [Cloud & Database Infrastructure](#cloud--database-infrastructure)
6. [How to Run](#how-to-run)
   - [Mode A: Local Development](#mode-a-local-development)
   - [Mode B: Cloud Production (24/7)](#mode-b-cloud-production-247)
7. [Reattaching to a Live Session](#reattaching-to-a-live-session)

---

## Overview

This directory contains the **spatial physics and forecasting engine** for the SEABeacon Regional Disaster Alert System. The pipeline operates as a **24/7 autonomous daemon** designed for cloud deployment and tracks live transboundary tropical cyclones in real time.

**Key capabilities:**
- Live ingestion from NASA EONET and GDACS APIs
- 17-feature meteorological tensor inference via XGBoost
- Autoregressive 72-hour forecast loop with dynamic uncertainty radii
- Persistent cloud logging via Supabase (PostGIS)

---

## System Architecture

The forecasting core follows a five-stage pipeline:

```
[1] INGEST          [2] VECTORIZE         [3] INFER
NASA EONET  ──►  17-feature tensor  ──►  XGBoost engine
GDACS              (lat, lon, wind,         (seabeacon_xgb_v1.pkl)
                    pressure, seasonal
                    sinusoids, ...)
                                                  │
                                                  ▼
[5] PERSIST                           [4] AUTOREGRESS
Supabase     ◄──  FastAPI server  ◄──  6 / 12 / 24 / 48 / 72 hr steps
(PostGIS)         (api/main.py)         + dynamic Landfall Risk Scope
```

| Stage | Description |
|---|---|
| **Ingestion** | Pings NASA EONET and GDACS APIs for live synoptic coordinate drops |
| **Vectorization** | Converts the raw payload into a 17-feature meteorological tensor |
| **Inference** | Feeds the vector into the pre-trained 3D XGBoost model |
| **Autoregression** | Kinematic feedback loop generating forecast steps at 6, 12, 24, 48, and 72 hours; outputs a dynamic **Landfall Risk Scope** (uncertainty radius) per step |
| **Persistence** | Routes spatial data through a local FastAPI server to a cloud-hosted Supabase PostgreSQL/PostGIS database |

---

## Model Performance

The current model artifact (`seabeacon_xgb_v1.pkl`) was trained on **NOAA IBTrACS** historical cyclone data (1980–present), extracting **30,965 valid multi-dimensional matrices**.

| Metric | Value |
|---|---|
| Intensity Error (Mean Absolute) | **3.39 knots** |
| Spatial Cross-Track Error (Median) | **38.40 km** per 6-hour prediction step |

> ⚠️ **Note on compounding error:** Because spatial error accumulates across the 72-hour autoregressive loop, the system outputs a **dynamic Landfall Risk Scope** at each step to safely encompass statistical deviation.

---

## Directory Structure

```
xgboost_forecast/
│
├── data/                            # Data warehouse (Git-ignored)
│   ├── raw/                         # Raw IBTrACS CSVs or live downloads
│   └── shapefiles/                  # GADM shapefiles: Philippines, Vietnam, Thailand
│
├── notebooks/                       # Experimentation & sandbox
│   ├── 01_exploration.ipynb
│   └── 02_spatial_migration.ipynb
│
├── src/                             # Core engine — Spatial Physics Pipeline
│   ├── data_pipeline/
│   │   ├── fetch_realtime.py        # Pings GDACS/JTWC API (live & historical replay)
│   │   ├── preprocess.py            # Physics functions & sliding window utilities
│   │   └── noru_playback.json       # Trajectory JSON for time-lapse simulation
│   ├── model/
│   │   ├── train.py                 # XGBoost training script
│   │   └── predict.py               # 72-hour autoregressive trajectory loop
│   └── nlp/                         # Phase 2: Social Media Engine
│       └── simulate_stream.py       # Geofenced crisis stream generator
│
├── automation/                      # 24/7 daemon & demo layer
│   ├── daemon.py                    # Hourly scheduler with deduplication
│   └── demo_runner.py               # Accelerated 72-hour simulation (5-second steps)
│
├── api/
│   └── main.py                      # FastAPI server: PostGIS routing + Supabase logging
│
├── integration/                     # Ensemble partner scripts
│   └── lstm_fetch_example.py        # REST fetcher for LSTM time-series ingestion
│
├── models/
│   └── seabeacon_xgb_v1.pkl         # Trained model artifact
│
├── .env                             # Local credentials (Git-ignored)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Cloud & Database Infrastructure

The pipeline uses a **decoupled architecture**: compute runs on Google Cloud, storage lives on Supabase.

### Supabase (PostgreSQL + PostGIS)

Supabase stores all 72-hour `Landfall Risk Scope` coordinates logged by the FastAPI server.

**Setup:**

1. Create a project at [supabase.com](https://supabase.com).
2. Create a table named `seabeacon_forecasts` with columns for: simulation run ID, latitude, longitude, wind speed, and risk radius.
3. Go to **Project Settings → Database → Connection string → URI**.
4. Create a `.env` file in the root of `xgboost_forecast/` and paste your connection string:

```env
DATABASE_URL="postgresql://postgres.[your-project]:[your-password]@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"
```

> ✅ `.env` is Git-ignored — your credentials are safe.

---

## How to Run

### Mode A: Local Development

Use this mode when modifying the XGBoost model, tweaking the 17-feature vector logic, or running historical backtests.

```bash
# 1. Navigate to the directory
cd SEABeacon-Regional-Disaster-Alert-System/phase1/xgboost_forecast

# 2. Activate the virtual environment
#    Windows:
.venv\Scripts\activate
#    Mac/Linux:
source .venv/bin/activate

# 3. Run a manual prediction (bypasses the 1-hour daemon sleep cycle)
python src/demo_runner.py
```

---

### Mode B: Cloud Production (24/7)

Use this mode when SSH'd into your Google Cloud server. Both the **API server** and **ingestion daemon** must run simultaneously — use `tmux` to keep both alive after you disconnect.

#### Step 1 — Prepare the environment

```bash
sudo apt update && sudo apt install python3-venv tmux -y
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### Step 2 — Create a persistent tmux session

```bash
tmux new -s seabeacon
```

#### Step 3 — Launch the Storage API (Window 1)

```bash
source .venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

#### Step 4 — Open a second window and launch the Daemon

Press `Ctrl+B` then `C` to open a new tmux window, then:

```bash
source .venv/bin/activate
python automation/daemon.py
```

#### Step 5 — Detach safely

Press `Ctrl+B` then `D` to detach from the session without stopping either process.

> 💡 You can also simply close your SSH window — both processes will continue running on the server, autonomously tracking NASA EONET and logging spatial data to Supabase.

---

## Reattaching to a Live Session

To check logs or stop the daemon after a previous deployment:

```bash
# SSH back into the server, then:
tmux attach -t seabeacon
```

You'll be dropped back into the running session with both windows active.