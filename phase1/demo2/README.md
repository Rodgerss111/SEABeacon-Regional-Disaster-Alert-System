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

## Run everything

**Windows (PowerShell):**
```powershell
./run_all.ps1
```

**macOS / Linux / Git-Bash:**
```sh
./run_all.sh
```

Each launcher starts the three backend daemons (each in its own window/process)
and the Vite dev server. Open the printed local URL (default
<http://localhost:5173>). Within ~30 s you should see flood, typhoon, and social
reports appearing on their own — no manual entry.

To stop: close the spawned windows (PowerShell) or press `Ctrl-C` in the
launching terminal (bash kills the backgrounded jobs on exit).

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

- **Not verified end-to-end here** — wiring is complete and the build compiles,
  but a live run needs real Supabase credentials and the LSTM weights, which are
  not in the repo.
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
