# SEABeacon — Demo 2: Full Integrated Prototype

This is the **end-to-end demo**: all three AI backends feeding the frontend fusion
engine live, with no manual slider entry required.

Unlike Demo 1 (in `../app/my-map-app`), where the frontend only auto-consumed the
**typhoon (XGBoost)** backend, this build adds two more pollers so the frontend
ingests **all three** AI sources automatically:

| AI source | Backend | Supabase table | Frontend poller |
|-----------|---------|----------------|-----------------|
| **AI-1 Flood** | `../lstm_model` (LSTM) | `flood_predictions` | ✅ added in demo2 |
| **AI-2 Typhoon** | `../xgboost_forecast` (XGBoost) | `seabeacon_forecasts` | ✅ already present |
| **AI-3 Social** | `../nlp_analysis` (XLM-R NLP) | `alerts` | ✅ added in demo2 |

All three poll every 30 s, normalize their outputs to the common report shape,
and flow into the same fusion engine → province rankings → confidence scoring →
three-tier alert protocol → human gate → aggregated multi-channel advisory.

---

## Architecture

```
 Open-Meteo            GDACS                 News sites
 (discharge/rain)      (typhoon track)       (PAGASA, Rappler, …)
      │                    │                       │
      ▼                    ▼                       ▼
 ┌──────────┐        ┌───────────┐          ┌────────────┐
 │ LSTM     │        │ XGBoost   │          │ XLM-R NLP  │
 │ main.py  │        │ daemon.py │          │ main.py    │
 └────┬─────┘        └─────┬─────┘          └─────┬──────┘
      │ flood_predictions  │ seabeacon_forecasts  │ alerts
      ▼                    ▼                       ▼
 ┌──────────┐        ┌───────────┐          ┌────────────┐
 │ AI-1 DB  │        │ AI-2 DB   │          │ AI-3 DB    │   (Supabase)
 └────┬─────┘        └─────┬─────┘          └─────┬──────┘
      │  poll 30s          │  poll 30s            │  poll 30s
      └────────────────────┼──────────────────────┘
                           ▼
              ┌─────────────────────────────┐
              │  Frontend (SEABeacon.jsx)   │
              │  fusion → rank → tier →      │
              │  human gate → advisory out   │
              └─────────────────────────────┘
```

---

## Prerequisites

- **Node.js 18+** and **npm**
- **Python 3.10+** (one venv per backend, or one shared venv)
- **Four Supabase projects** (AI-1, AI-2, AI-3, Central) with their tables created
- The **LSTM model weights** placed in `../lstm_model/model/` (see that folder's
  README — `best_model_phase2.keras` is **not** committed and must be downloaded)

---

## One-time setup

### 1. Configure each backend's `.env`
Each backend reads its own `.env`. Copy the templates and fill in real values:

```sh
cp ../lstm_model/.env.example       ../lstm_model/.env
cp ../xgboost_forecast/.env.example ../xgboost_forecast/.env
cp ../nlp_analysis/.env.example     ../nlp_analysis/.env
```

### 2. Configure the frontend `.env`
```sh
cp frontend/.env.example frontend/.env
```
Then fill in **all four** Supabase URL/anon-key pairs in `frontend/.env`
(`VITE_AI1_*`, `VITE_AI2_*`, `VITE_AI3_*`, `VITE_CENTRAL_*`).
In Demo 2, AI-1 and AI-3 are now **actually used** — leaving them blank simply
disables those pollers (the app still runs on AI-2 + manual input).

### 3. Install dependencies
```sh
# Frontend
cd frontend && npm install && cd ..

# Backends (per backend, ideally in a venv)
pip install -r ../lstm_model/requirements.txt
pip install -r ../xgboost_forecast/requirements.txt
pip install -r ../nlp_analysis/requirements.txt
```

### 4. Seed history (so the daemons produce output immediately)
```sh
python ../lstm_model/live_seed.py    # 7 days of real Open-Meteo history for the LSTM
python ../nlp_analysis/demo_seed.py  # verified Sept–Oct 2022 articles (optional)
```

---

## Running the demo

There are two ways to run this, depending on whether you just want to **see the
integrated pipeline** (almost always what you want) or also **regenerate the data
locally** by running the AI producers yourself.

### Option A — Frontend only (recommended for the demo)

The three backends already write to shared Supabase, so the frontend alone shows
the complete end-to-end pipeline on real data. Nothing else needs to run.

**Windows (PowerShell):**
```powershell
cd frontend
npm install     # first time only
npm run dev
```
Open the URL it prints (e.g. <http://localhost:5173>). Within ~30 s, flood,
typhoon, and social reports appear on their own — no manual entry. To stop, press
`Ctrl-C` in that terminal.

### Option B — Full pipeline (frontend + the 3 AI producers)

Only needed if you want the Supabase tables to keep **refreshing live** from your
own machine. This is **4 processes** — the 3 Python daemons plus the frontend —
and each daemon has its own setup. Run each in its own terminal:

```powershell
# 1. LSTM — flood (writes flood_predictions)
cd ..\lstm_model
python -m venv venv; .\venv\Scripts\Activate.ps1
pip install -r requirements.txt        # TensorFlow 2.19 — large, slow first time
python live_seed.py                     # seed 7 days of history (run once)
python main.py                          # hourly daemon

# 2. XGBoost — typhoon (writes seabeacon_forecasts)
cd ..\xgboost_forecast
#   requires a local PostGIS database; copy .env.example -> .env and fill DATABASE_URL
pip install -r requirements.txt
python automation\daemon.py

# 3. NLP — social (writes alerts)
cd ..\nlp_analysis
#   requires the trained XLM-R model at MODEL_PATH (./models/xlmr_weather_model)
pip install -r requirements.txt        # torch + transformers — large
python main.py

# 4. Frontend
cd ..\demo2\frontend
npm run dev
```

**Readiness note (current repo state):** only the **LSTM** is ready to run
out-of-the-box (its `.env` and weights are present). **XGBoost** additionally
needs a local **PostGIS** instance and its `.env`; **NLP** needs the XLM-R model
folder downloaded. If you only want one live producer for the demo, run the LSTM.

### One-shot launcher

```powershell
./run_all.ps1     # Windows
./run_all.sh      # macOS / Linux / Git-Bash
```
Starts all three daemons (each in its own window) then the frontend. ⚠️ With the
current repo state this fully succeeds only for **LSTM + frontend** — XGBoost and
NLP will error out until their PostGIS/model prerequisites above are met. The
frontend runs fine regardless. To stop: close the spawned windows (PowerShell) or
press `Ctrl-C` in the launching terminal (bash kills the backgrounded jobs).

---

## What changed vs. Demo 1 (for reviewers)

The **only** functional code change is in
[`frontend/src/SEABeacon.jsx`](frontend/src/SEABeacon.jsx): two new `useEffect`
pollers (search for `AI-1 (Flood / LSTM) processor` and
`AI-3 (Social / NLP) processor`). They mirror the existing AI-2 forecast poller —
fetch latest rows, dedup, normalize to the common report shape, and call
`handleSubmit`. Everything downstream (fusion, tiers, human gate, dispatch) was
already source-agnostic, so no other change was needed.

## Caveats

- **Verified connected** — the frontend authenticates against all four Supabase
  projects and ingests live `flood_predictions`, `seabeacon_forecasts`, and
  `alerts` rows. Whether each table keeps *refreshing* depends on the producer
  daemons running (Option B); Option A reads whatever the shared databases
  currently hold.
- **Typhoon fallback** — the AI-2 poller processes the most recent forecast run
  that actually has province impacts (within a 6 h freshness window), so the map
  isn't blank when the very latest cycle happens to be `NO_IMPACT_DETECTED`.
- **Province-name normalization** *(handled)*: the backends don't agree on
  spellings — XGBoost emits country `"Philippines"`, and province names vary by
  spaces/diacritics (`"QuảngBình"` vs `"Quang Binh"`). The UI uses ISO codes
  `PH` / `VN` / `TH`. `normalizeReport()` in `SEABeacon.jsx` canonicalizes
  country + province at ingest (in `handleSubmit`, the single path all four
  sources share) so fusion groups them correctly; a legacy `VT`→`VN` alias keeps
  older Vietnam data working. Genuinely unknown provinces pass through unchanged
  rather than being dropped.
- The flood/social pollers dedup **in-memory** (per page session). A full reload
  re-ingests recent rows; that's harmless for a demo (they re-expire after 6 h).
