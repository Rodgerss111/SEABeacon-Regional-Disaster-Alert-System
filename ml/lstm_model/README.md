# SEABeacon — Component A: Flood LSTM (Phase 1)

Flood Threshold Prediction model for the SEABeacon Regional Disaster Alert
System (ASEAN AI Hackathon 2026, CardinalMu ASEAN, Mapúa University).

Predicts flood probability and severity tier (Normal / Watch / Advisory /
Warning) for 7 river basins across the Philippines, Vietnam, and Thailand,
using an LSTM with Luong attention trained on river discharge, rainfall,
soil moisture, and typhoon proximity features.

---

## Folder Contents

| File | Purpose |
|---|---|
| `config.py` | Loads `.env`, defines all constants (paths, thresholds, basin radii) |
| `db.py` | All Supabase reads/writes (`flood_raw_operational`, `flood_predictions`, fetch log) |
| `model_loader.py` | Custom Keras layer/loss classes + `load_artifacts()` |
| `features.py` | Feature engineering, typhoon proximity, flood-arrival-window heuristic |
| `live_data.py` | Live sensor fetchers via Open-Meteo (live mode only) |
| `typhoon_client.py` | Fetches typhoon forecasts from Component B's Supabase (live + demo) |
| `inference.py` | Shared per-basin inference logic (used by both live and demo) |
| `demo_seed.py` | **Run once** — backfills 55 historical rows simulating Typhoon Karding/Noru |
| `demo_run.py` | **Demo entrypoint** — one inference cycle against the seeded scenario |
| `main.py` | **Production entrypoint** — continuous polling daemon (1-hour cycle) |
| `requirements.txt` | Python dependencies |
| `.env.example` | Template for required secrets — copy to `.env` and fill in |
| `model/` | **You must add 4 files here yourself** — see below |

---

## ⚠️ Required Files NOT Included in This Folder

The trained model artifacts are stored as a **Kaggle Model**, not committed
directly to this repo folder (they're tracked via Git LFS once added).
Before running anything, download these 4 files from your Kaggle Model
output and place them inside `model/`:

```
model/
├── best_model_phase2.keras
├── scaler_params_v2.json
├── feature_cols.json
└── basin_meta.csv
```

Without these 4 files, every script in this folder will fail at
`model_loader.load_artifacts()`.

---

## Setup (One-Time)

### 1. Clone the repo and enter this folder
```bash
git clone https://github.com/IgnateGav/SEABeacon-Regional-Disaster-Alert-System.git
cd SEABeacon-Regional-Disaster-Alert-System/phase1/lstm_model
```

### 2. Create a virtual environment and install dependencies
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Add the model artifacts
Download the 4 files listed above from your Kaggle Model and place them
in `model/` (create the folder if it doesn't exist).

### 4. Set up your secrets
```bash
cp .env.example .env
```
Open `.env` and fill in:
- `SUPABASE_URL` and `SUPABASE_KEY` — from your **AI-1 Flood Prediction**
  Supabase project → Project Settings → API
- `COMPONENT_B_ANON_KEY` — ask your Component B (typhoon) teammate for
  their project's anon key

`.env` is already in `.gitignore` — never commit it.

---

## Running

### Demo mode (for judges — reproducible Karding/Noru replay)
```bash
python demo_seed.py     # run once: seeds historical scenario data
python demo_run.py      # runs one inference cycle, prints + writes results
```
You can re-run `demo_run.py` as many times as you like — it always replays
the same fixed scenario, so the demo is consistent every time you show it.

Before running, open `demo_run.py` and confirm `DEMO_SIMULATION_RUN_ID`
and `DEMO_STORM_NAME` match the exact values in Component B's database —
ask your Component B teammate to confirm these strings if unsure.

### Live mode (production — real continuous monitoring)
```bash
python main.py
```
This runs forever, polling live data every hour, fetching the latest
typhoon forecast from Component B, running inference, and writing results
to Supabase. Stop with `Ctrl+C`.

---

## How Predictions Reach the Rest of SEABeacon

Every inference cycle writes rows to the `flood_predictions` table in
**your own** Supabase project (`AI-1 Flood Prediction`). The integration
teammate's confidence-scoring service reads from this table — and the
equivalent tables from Component B (typhoon) and Component C (NLP
sentiment) — joining them by `province` to compute the final combined
confidence score shown on the dashboard.

```
Component A (this folder) ──┐
Component B (xgboost_forecast) ──┼──> Confidence Scoring Engine ──> Alert
Component C (nlp_analysis) ──┘
```

---

## Output Schema

Each basin produces one record per inference cycle:

```json
{
  "province": "Pampanga",
  "country": "PH",
  "score_type": "physical_flood",
  "score_value": 0.64,
  "expires_at": "2026-06-19T18:13:15Z",
  "context": {
    "basin_name": "Ph Luzon Central",
    "discharge_cms": 86.80,
    "threshold_cms": 86.7969,
    "forecast_horizon_hrs": 36,
    "severity_label": "WARNING",
    "affected_provinces": ["Pampanga", "Bulacan", "Nueva Ecija", "Tarlac"],
    "expected_onset_hrs": 14.5,
    "expected_peak_hrs": 23.5,
    "expected_end_hrs": 32.5,
    "typhoon_name": "Super Typhoon Noru (Karding)",
    "typhoon_dist_km": 80.0,
    "typhoon_wind_kmh": 185.0,
    "typhoon_category": 5,
    "hours_to_landfall": 14.5
  }
}
```

`discharge_cms` and `threshold_cms` are both in **m³/s** (cubic meters per
second) — how much water is flowing through the river right now, versus
the model-derived discharge level above which that basin is considered
flooding.

---

## Troubleshooting

| Problem | Likely Cause |
|---|---|
| `FileNotFoundError: model/best_model_phase2.keras` | You haven't downloaded the model artifacts — see "Required Files" above |
| `RuntimeError: Missing required environment variable` | `.env` doesn't exist or is missing a key — copy from `.env.example` |
| Inference always returns `None` for every basin | Run `demo_seed.py` first (demo mode) — fewer than 56 history rows exist |
| Wrong typhoon name appears in output | `DEMO_SIMULATION_RUN_ID` / `DEMO_STORM_NAME` in `demo_run.py` don't match Component B's actual data — confirm exact strings with that teammate |
| `Could not reach Component B` | Check `COMPONENT_B_ANON_KEY` is correct and Component B's Supabase project is up |

---

## Model Details

- **Architecture:** 2-layer LSTM encoder + Luong attention + dense heads
  (flood probability, severity tier, discharge regression)
- **Lookback window:** 56 steps × 3 hours = 168 hours (7 days)
- **Forecast horizon:** 36 hours ahead
- **Decision threshold:** 0.22 (tuned for higher recall on rare flood tiers)
- **Loss function:** Focal loss (γ=2.0, α=0.85) — addresses severe class
  imbalance between Normal and flood-tier samples
- **Basins monitored:** PH_LUZON_NORTH, PH_LUZON_CENTRAL, PH_VISAYAS,
  PH_MINDANAO, VN_CENTRAL, VN_MEKONG, TH_CHAOPHRAYA

---

*SEABeacon · CardinalMu ASEAN · Mapúa University · ASEAN AI Hackathon 2026*
