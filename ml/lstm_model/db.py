"""
SEABeacon — Component A: Flood LSTM
db.py

All Supabase reads/writes for Component A's own database
(flood_raw_operational, flood_predictions, component_b_fetch_log).
"""

import json
from datetime import datetime, timezone, timedelta

import pandas as pd
from supabase import create_client

import config

# ── Single shared Supabase client for this process ─────────────────────────
sb = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)


# ── flood_raw_operational ───────────────────────────────────────────────────

def get_recent_window(basin_id: str, lookback_days: int = config.RAW_RETENTION_DAYS,
                      reference_time: datetime = None) -> pd.DataFrame:
    """
    Returns the recent rows for one basin as a time-indexed DataFrame.
    reference_time: pass a fixed datetime for demo mode; None uses real "now".
    """
    now = reference_time or datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=lookback_days)).isoformat()
    resp = (
        sb.table("flood_raw_operational")
        .select("*")
        .eq("basin_id", basin_id)
        .gte("timestamp_utc", cutoff)
        .order("timestamp_utc", desc=False)
        .execute()
    )
    df = pd.DataFrame(resp.data)
    if df.empty:
        return df
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    return df.set_index("timestamp_utc").sort_index()


def write_raw(basin_id: str, row: dict) -> None:
    """Upserts one row of live/backfilled sensor data for a basin."""
    sb.table("flood_raw_operational").upsert(
        row, on_conflict="timestamp_utc,basin_id"
    ).execute()


def write_raw_batch(rows: list, batch_size: int = 100) -> None:
    """Upserts many rows at once, chunked to stay under request size limits."""
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        sb.table("flood_raw_operational").upsert(
            batch, on_conflict="timestamp_utc,basin_id"
        ).execute()
        print(f"  Inserted rows {i + 1}-{min(i + batch_size, len(rows))}")


def cleanup_old_raw(basin_id: str, retention_days: int = config.RAW_RETENTION_DAYS) -> None:
    """Deletes raw rows older than retention_days for one basin."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
    sb.table("flood_raw_operational").delete() \
        .eq("basin_id", basin_id).lt("timestamp_utc", cutoff).execute()


# ── flood_predictions ───────────────────────────────────────────────────────

def write_predictions(predictions: list, cleanup: bool = True) -> None:
    """
    Inserts one row per basin prediction into flood_predictions (history mode —
    every inference cycle is kept, not overwritten, so judges can see the
    full timeline of how confidence evolved during a typhoon).
    """
    rows = [
        {
            "province":           p["province"],
            "country":            p["country"],
            "basin_id":           p["context"]["basin_name"].replace(" ", "_").upper(),
            "score_value":        p["score_value"],
            "severity_label":     p["context"]["severity_label"],
            "discharge_cms":      p["context"]["discharge_cms"],
            "threshold_cms":      p["context"]["threshold_cms"],
            "forecast_hrs":       p["context"]["forecast_horizon_hrs"],
            "expires_at":         p["expires_at"],
            "affected_provinces": json.dumps(p["context"]["affected_provinces"]),
            "expected_onset_hrs": p["context"]["expected_onset_hrs"],
            "expected_peak_hrs":  p["context"]["expected_peak_hrs"],
            "expected_end_hrs":   p["context"]["expected_end_hrs"],
            "typhoon_name":       p["context"].get("typhoon_name"),
        }
        for p in predictions
    ]
    sb.table("flood_predictions").insert(rows).execute()
    print(f"Wrote {len(rows)} predictions to flood_predictions.")

    if cleanup:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=config.PRED_RETENTION_DAYS)).isoformat()
        sb.table("flood_predictions").delete().lt("run_timestamp", cutoff).execute()


# ── component_b_fetch_log ───────────────────────────────────────────────────

def log_component_b_fetch(nodes: list, simulation_run_id: str,
                          fetched_at: datetime = None) -> None:
    """Logs every typhoon node pulled from Component B, for audit purposes."""
    if not nodes:
        return
    now_iso = (fetched_at or datetime.now(timezone.utc)).isoformat()
    log_rows = [
        {
            "fetched_at":           now_iso,
            "simulation_run_id":    simulation_run_id,
            "forecast_target_time": n["forecast_target_time"],
            "predicted_lat":        n["predicted_lat"],
            "predicted_lon":        n["predicted_lon"],
            "predicted_wind_kph":   n["predicted_wind_kph"],
        }
        for n in nodes
    ]
    try:
        sb.table("component_b_fetch_log").insert(log_rows).execute()
        print(f"  Logged {len(log_rows)} nodes to component_b_fetch_log.")
    except Exception as e:
        print(f"  component_b_fetch_log write failed: {e}")


# ── Daemon state (so a restarted process remembers where it left off) ──────

def load_last_state() -> dict:
    if config.STATE_FILE.exists():
        with open(config.STATE_FILE) as f:
            return json.load(f)
    return {"last_run_timestamp": None, "last_typhoon_run_id": None}


def save_state(run_timestamp: str, typhoon_run_id: str) -> None:
    with open(config.STATE_FILE, "w") as f:
        json.dump(
            {"last_run_timestamp": run_timestamp, "last_typhoon_run_id": typhoon_run_id},
            f,
        )
