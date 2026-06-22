"""
SEABeacon — Component A: Flood LSTM
live_data.py

Live sensor data fetchers, all via Open-Meteo (free, no API key required).
Used only by main.py (the live continuous daemon) — NOT used by the demo
scripts, which read from backfilled Supabase rows instead.
"""

from datetime import datetime, timezone

import requests


def fetch_live_discharge(lat: float, lon: float) -> float | None:
    """
    River discharge via Open-Meteo Flood API (GloFAS-derived, plain JSON).
    https://open-meteo.com/en/docs/flood-api
    Returns the most recent daily value in m3/s, or None if unavailable.
    """
    url = (
        f"https://flood-api.open-meteo.com/v1/flood"
        f"?latitude={lat}&longitude={lon}&daily=river_discharge"
        f"&past_days=2&forecast_days=1"
    )
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            vals = r.json().get("daily", {}).get("river_discharge", [])
            valid = [v for v in vals if v is not None]
            if valid:
                return float(valid[-1])
            print(f"    Flood API: no discharge values for ({lat},{lon})")
        else:
            print(f"    Flood API HTTP {r.status_code}")
    except Exception as e:
        print(f"    Discharge fetch failed: {e}")
    return None


def fetch_live_rainfall(lat: float, lon: float) -> float | None:
    """
    Hourly precipitation via Open-Meteo Weather API.
    Returns mm accumulated over the last 3 hours, or None if unavailable.
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}&hourly=precipitation"
        f"&past_days=1&forecast_days=1"
    )
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            data    = r.json()
            times   = data.get("hourly", {}).get("time", [])
            precip  = data.get("hourly", {}).get("precipitation", [])
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:00")
            try:
                idx = times.index(now_str)
            except ValueError:
                idx = len(times) - 1
            window = precip[max(0, idx - 2): idx + 1]
            return float(sum(v for v in window if v is not None))
        else:
            print(f"    Rainfall API HTTP {r.status_code}")
    except Exception as e:
        print(f"    Rainfall fetch failed: {e}")
    return None


def fetch_live_soil_moisture(lat: float, lon: float) -> float | None:
    """Top-7cm soil moisture via Open-Meteo Weather API (confirmed reliable)."""
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}"
        f"&longitude={lon}&current=soil_moisture_0_to_7cm"
    )
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            sm = r.json().get("current", {}).get("soil_moisture_0_to_7cm")
            if sm is not None:
                return float(sm)
    except Exception as e:
        print(f"    Soil moisture fetch failed: {e}")
    return None
