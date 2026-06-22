"""
SEABeacon — Component A: Flood LSTM
config.py

Central configuration. Loads secrets from .env (local) or from the real
environment (if deployed on a server that sets env vars directly).

Mirrors the .env / config.py pattern used in xgboost_forecast and nlp_analysis.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env file from the same folder as this script ────────────────────
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def get_secret(key: str) -> str:
    """Reads a required secret from environment variables (loaded from .env)."""
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {key}\n"
            f"Did you create a .env file from .env.example and fill it in?"
        )
    return value


# ── Supabase credentials (Component A's own database) ─────────────────────
SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")

# ── Component B's Supabase project (read-only access to typhoon forecasts) ─
COMPONENT_B_ANON_KEY = get_secret("COMPONENT_B_ANON_KEY")
COMPONENT_B_PROJECT_REF = "axigjjehzqghflrvewaj"
COMPONENT_B_TABLE = "seabeacon_forecasts"
COMPONENT_B_URL = f"https://{COMPONENT_B_PROJECT_REF}.supabase.co/rest/v1/{COMPONENT_B_TABLE}"

# ── Model artifact paths (all four files must exist in ./model/) ──────────
ARTIFACTS_DIR   = BASE_DIR / "model"
MODEL_PATH      = ARTIFACTS_DIR / "best_model_phase2.keras"
SCALER_PATH     = ARTIFACTS_DIR / "scaler_params_v2.json"
FEATURES_PATH   = ARTIFACTS_DIR / "feature_cols.json"
BASIN_META_PATH = ARTIFACTS_DIR / "basin_meta.csv"

# ── Model / inference constants (must match training notebook exactly) ────
SEQUENCE_LENGTH     = 56
DECISION_THRESHOLD  = 0.22
RAW_RETENTION_DAYS  = 14
PRED_RETENTION_DAYS = 30
TIER_NAMES = {0: "Normal", 1: "Watch", 2: "Advisory", 3: "Warning"}

# Per-basin search radius (km) for "is a typhoon close enough to matter?"
TYPHOON_RADIUS_KM = {
    "PH_LUZON_NORTH":   500,
    "PH_LUZON_CENTRAL": 500,
    "PH_VISAYAS":       500,
    "PH_MINDANAO":      500,
    "VN_CENTRAL":       600,
    "VN_MEKONG":        600,
    "TH_CHAOPHRAYA":    800,
}

# ── State file for the live daemon (remembers last run across restarts) ───
STATE_FILE = BASE_DIR / "seabeacon_a_last_state.json"
