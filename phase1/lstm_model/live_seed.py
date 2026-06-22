"""
SEABeacon — Component A: Flood LSTM
live_seed.py

LIVE SEED — run this ONCE whenever flood_raw_operational is empty and you
need to prime the 56-step history window before main.py can produce
predictions. Uses REAL historical data from Open-Meteo (same provider as
live polling) for the last 7 days, so the seed rows match the live data
distribution exactly.

56 steps * 3h = 7 days of history, one row per basin per 3-hour slot.

Usage:
    python live_seed.py          # seeds using real past 7 days
    python live_seed.py --check  # just prints row counts without seeding

Run this before starting main.py on a fresh Supabase table.
DO NOT run demo_seed.py before main.py — demo_seed writes synthetic
typhoon-storm data which will distort the live model's history window.
"""

import sys
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta

import db

# ── Basin definitions — must match config.py exactly ───────────────────────
BASINS = [
    {"basin_id": "PH_LUZON_NORTH",   "lat": 18.0, "lon": 121.8},
    {"basin_id": "PH_LUZON_CENTRAL", "lat": 15.5, "lon": 120.7},
    {"basin_id": "PH_VISAYAS",       "lat": 11.2, "lon": 124.8},
    {"basin_id": "PH_MINDANAO",      "lat":  8.0, "lon": 125.5},
    {"basin_id": "VN_CENTRAL",       "lat": 15.8, "lon": 108.2},
    {"basin_id": "VN_MEKONG",        "lat": 11.0, "lon": 106.0},
    {"basin_id": "TH_CHAOPHRAYA",    "lat": 14.5, "lon": 100.5},
]

# 56 steps × 3h = 7 days.  Each step is one 3-hour slot.
SEQUENCE_LENGTH = 56
STEP_HOURS      = 3
PAST_DAYS       = 7          # how many days back Open-Meteo should return


# ── Open-Meteo fetchers (identical behaviour to live_data.py) ───────────────

def _fetch_discharge_history(lat: float, lon: float) -> pd.Series:
    """
    River discharge for the past PAST_DAYS + 1 days via Open-Meteo Flood API.
    Returns a pandas Series indexed by date (daily resolution).
    """
    url = (
        f"https://flood-api.open-meteo.com/v1/flood"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=river_discharge&past_days={PAST_DAYS + 1}&forecast_days=0"
    )
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        dates  = data["daily"]["time"]
        values = data["daily"]["river_discharge"]
        # s = pd.Series(values, index=pd.to_datetime(dates), dtype=float)
        s = pd.Series(values, index=pd.to_datetime(dates).tz_localize('UTC'), dtype=float)
        return s.dropna()
    except Exception as e:
        print(f"    discharge history fetch failed: {e}")
        return pd.Series(dtype=float)


def _fetch_weather_history(lat: float, lon: float) -> pd.DataFrame:
    """
    Hourly precipitation + soil moisture for the past PAST_DAYS + 1 days.
    Returns DataFrame with columns: precipitation (mm/hr), soil_moisture (m³/m³).
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&hourly=precipitation,soil_moisture_0_to_7cm"
        f"&past_days={PAST_DAYS + 1}&forecast_days=0"
    )
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data  = r.json()["hourly"]
        times = pd.to_datetime(data["time"]).tz_localize('UTC')
        df = pd.DataFrame({
            "precipitation": data["precipitation"],
            "soil_moisture": data["soil_moisture_0_to_7cm"],
        }, index=times)
        return df.dropna(how="all")
    except Exception as e:
        print(f"    weather history fetch failed: {e}")
        return pd.DataFrame(columns=["precipitation", "soil_moisture"])


def _build_3hourly_rows(basin_id: str, lat: float, lon: float,
                         end_utc: datetime) -> list:
    """
    Builds exactly SEQUENCE_LENGTH rows at 3-hour intervals ending at end_utc.

    discharge_cms  — from Open-Meteo Flood API (daily), forward-filled to 3h
    precip_mm_3h   — 3-hour sum of Open-Meteo hourly precipitation
    soil_moisture  — Open-Meteo hourly soil moisture, resampled to 3h mean

    All values are real historical data for the basin's lat/lon.
    """
    print(f"  Fetching {PAST_DAYS}-day history for {basin_id} ({lat}, {lon})...")

    discharge_daily = _fetch_discharge_history(lat, lon)
    weather_hourly  = _fetch_weather_history(lat, lon)

    # Build the target 3-hourly timestamp grid (oldest → newest)
    start_utc = end_utc - timedelta(hours=STEP_HOURS * SEQUENCE_LENGTH)
    ts_index  = pd.date_range(
        start=start_utc + timedelta(hours=STEP_HOURS),
        end=end_utc,
        freq=f"{STEP_HOURS}h",
        tz="UTC",
    )

    rows = []
    for ts in ts_index:
        # ── discharge_cms ─────────────────────────────────────────────────────
        # Daily discharge → forward-fill to 3-hourly by matching the date
        if not discharge_daily.empty:
            date_key = ts.normalize()
            # Find most recent daily value at or before this timestamp
            past_daily = discharge_daily[discharge_daily.index <= date_key]
            if not past_daily.empty:
                discharge = float(past_daily.iloc[-1])
            else:
                # Before series start — use first available value
                discharge = float(discharge_daily.iloc[0]) \
                    if not discharge_daily.empty else 0.0
        else:
            discharge = 0.0

        # ── precip_mm_3h ──────────────────────────────────────────────────────
        # Sum 3 hourly precipitation values ending at this timestamp
        if not weather_hourly.empty and "precipitation" in weather_hourly.columns:
            window_start = ts - timedelta(hours=STEP_HOURS - 1)
            window_end   = ts
            mask = (weather_hourly.index >= window_start) & \
                   (weather_hourly.index <= window_end)
            rain_window = weather_hourly.loc[mask, "precipitation"].dropna()
            precip = float(rain_window.sum()) if not rain_window.empty else 0.0
        else:
            precip = 0.0

        # ── soil_moisture ─────────────────────────────────────────────────────
        # Mean soil moisture over the same 3-hour window
        if not weather_hourly.empty and "soil_moisture" in weather_hourly.columns:
            window_start = ts - timedelta(hours=STEP_HOURS - 1)
            mask = (weather_hourly.index >= window_start) & \
                   (weather_hourly.index <= ts)
            sm_window = weather_hourly.loc[mask, "soil_moisture"].dropna()
            soil_m = float(sm_window.mean()) if not sm_window.empty else 0.3
        else:
            soil_m = 0.3

        rows.append({
            "timestamp_utc":    ts.isoformat(),
            "basin_id":         basin_id,
            "discharge_cms":    round(max(discharge, 0.0), 4),
            "precip_mm_3h":     round(max(precip,   0.0), 4),
            "soil_moisture":    round(float(np.clip(soil_m, 0.0, 1.0)), 4),
            "typhoon_dist_km":  None,   # no active typhoon during normal seeding
            "typhoon_wind_kmh": None,
            "typhoon_name":     None,
        })

    fetched_q  = sum(1 for r in rows if r["discharge_cms"] > 0)
    fetched_p  = sum(1 for r in rows if r["precip_mm_3h"] > 0)
    fetched_sm = sum(1 for r in rows if r["soil_moisture"] > 0)
    print(f"    {len(rows)} rows built | "
          f"discharge: {fetched_q}/{len(rows)} | "
          f"rain: {fetched_p}/{len(rows)} | "
          f"soil: {fetched_sm}/{len(rows)}")
    return rows


def check_existing_rows():
    """Print current row count per basin — useful for checking if seed is needed."""
    print("\nCurrent row counts in flood_raw_operational:")
    for basin in BASINS:
        bid = basin["basin_id"]
        resp = db.get_recent_window(bid, lookback_days=8)
        n = len(resp) if not resp.empty else 0
        status = "OK (ready)" if n >= SEQUENCE_LENGTH else f"NEEDS SEED ({n}/{SEQUENCE_LENGTH})"
        print(f"  {bid}: {n} rows — {status}")
    print()


def main():
    if "--check" in sys.argv:
        check_existing_rows()
        return

    # Snap "now" to the nearest 3-hour boundary (same logic as main.py)
    now_utc = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    now_utc = now_utc.replace(hour=(now_utc.hour // 3) * 3)

    print("=" * 60)
    print("SEABeacon Component A — Live Historical Seed")
    print(f"Seeding 7 days of real data ending at: {now_utc.isoformat()}")
    print(f"Basins: {[b['basin_id'] for b in BASINS]}")
    print("=" * 60)

    # Optional: warn if rows already exist (don't accidentally double-seed)
    print("\nChecking existing data before seeding...")
    existing_counts = {}
    for basin in BASINS:
        bid = basin["basin_id"]
        resp = db.get_recent_window(bid, lookback_days=8)
        existing_counts[bid] = len(resp) if not resp.empty else 0

    already_seeded = [bid for bid, n in existing_counts.items() if n >= SEQUENCE_LENGTH]
    if already_seeded:
        print(f"\nWARNING: These basins already have {SEQUENCE_LENGTH}+ rows:")
        for bid in already_seeded:
            print(f"  {bid}: {existing_counts[bid]} rows")
        ans = input("\nSeed anyway? This will add duplicate timestamps (upsert). [y/N]: ")
        if ans.strip().lower() != "y":
            print("Aborted. Run with --check to inspect current row counts.")
            return

    # Fetch and write
    all_rows = []
    for basin in BASINS:
        rows = _build_3hourly_rows(
            basin["basin_id"], basin["lat"], basin["lon"], now_utc
        )
        all_rows.extend(rows)

    total = len(all_rows)
    per_basin = total // len(BASINS) if BASINS else 0
    print(f"\nTotal rows to write: {total} ({per_basin} per basin)")

    print("Writing to Supabase flood_raw_operational...")
    db.write_raw_batch(all_rows)

    print("\nSeed complete.")
    check_existing_rows()
    print("You can now run:  python main.py")


if __name__ == "__main__":
    main()