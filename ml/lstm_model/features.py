"""
SEABeacon — Component A: Flood LSTM
features.py

Feature engineering (must match training notebook exactly), typhoon
proximity calculation, and the flood-arrival-window heuristic.
"""

from datetime import datetime, timezone

import numpy as np
import pandas as pd


def engineer_features(df: pd.DataFrame, basin: dict) -> pd.DataFrame:
    """
    Builds the full feature set from raw discharge/precip/soil_moisture
    columns. Must be IDENTICAL to the feature engineering used in training,
    or the model receives inputs it has never seen the shape/scale of.
    """
    df = df.copy()
    flood_cms = basin["flood_cms"]

    df["rain_6h"]  = df["precip_mm_3h"].rolling(2,  min_periods=1).sum()
    df["rain_12h"] = df["precip_mm_3h"].rolling(4,  min_periods=1).sum()
    df["rain_24h"] = df["precip_mm_3h"].rolling(8,  min_periods=1).sum()
    df["rain_48h"] = df["precip_mm_3h"].rolling(16, min_periods=1).sum()
    df["rain_72h"] = df["precip_mm_3h"].rolling(24, min_periods=1).sum()

    df["rain_delta"]        = df["precip_mm_3h"].diff().fillna(0)
    df["discharge_lag_3h"]  = df["discharge_cms"].shift(1)
    df["discharge_lag_6h"]  = df["discharge_cms"].shift(2)
    df["discharge_lag_12h"] = df["discharge_cms"].shift(4)
    df["discharge_lag_24h"] = df["discharge_cms"].shift(8)

    df["hour_sin"]  = np.sin(2 * np.pi * df.index.hour  / 24)
    df["hour_cos"]  = np.cos(2 * np.pi * df.index.hour  / 24)
    df["month_sin"] = np.sin(2 * np.pi * df.index.month / 12)
    df["month_cos"] = np.cos(2 * np.pi * df.index.month / 12)

    df["discharge_ratio"] = (df["discharge_cms"] / max(flood_cms, 1e-6)).clip(0, 2.0)

    monthly_mean = df.groupby(df.index.month)["precip_mm_3h"].transform("mean")
    monthly_std  = df.groupby(df.index.month)["precip_mm_3h"].transform("std")
    df["rain_anomaly"] = ((df["precip_mm_3h"] - monthly_mean) / (monthly_std + 1e-6)).clip(-3, 5)

    return df.bfill().ffill()


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance between two lat/lon points, in kilometers."""
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def nearest_typhoon_to_basin(basin: dict, typhoon_nodes: list, radius_km: float = 500,
                             reference_time: datetime = None) -> dict:
    """
    Finds the closest typhoon forecast node to a basin's centroid and
    returns proximity/intensity features for the model.

    reference_time: pass a fixed datetime for demo mode (so hours_to_landfall
    is computed against the demo timeline, not real wall-clock time).
    None = live mode, uses datetime.now(timezone.utc).
    """
    now = reference_time or datetime.now(timezone.utc)

    if not typhoon_nodes:
        return {
            "typhoon_active": 0.0, "typhoon_dist_km": float(radius_km),
            "typhoon_wind_kmh": 0.0, "typhoon_category": 0.0,
            "hours_to_landfall": float(radius_km / 25.0),
        }

    blat, blon = basin["lat"], basin["lon"]
    best, best_dist = None, float("inf")
    for node in typhoon_nodes:
        d = haversine_km(node["predicted_lat"], node["predicted_lon"], blat, blon)
        if d < best_dist:
            best_dist, best = d, node

    if best is None or best_dist > radius_km:
        return {
            "typhoon_active": 0.0,
            "typhoon_dist_km": round(best_dist, 1) if best else float(radius_km),
            "typhoon_wind_kmh": 0.0, "typhoon_category": 0.0,
            "hours_to_landfall": float(radius_km / 25.0),
        }

    wind_kmh = float(best["predicted_wind_kph"])
    wind_kt  = wind_kmh / 1.852
    category = min(int(np.digitize(wind_kt, [33, 63, 82, 95, 112, 136])), 5)

    target_time = pd.to_datetime(best["forecast_target_time"], utc=True)
    hours_to_landfall = (target_time - now).total_seconds() / 3600.0

    return {
        "typhoon_active": 1.0, "typhoon_dist_km": round(best_dist, 1),
        "typhoon_wind_kmh": round(wind_kmh, 1), "typhoon_category": float(category),
        "hours_to_landfall": round(hours_to_landfall, 1),
    }


def estimate_flood_arrival(hours_to_landfall) -> dict:
    """
    Translates typhoon landfall timing into a human-readable flood window
    for the alert message. Simple explainable heuristic, not a model:
      - Typhoon approaching: flood risk peaks ~9h after landfall, clears ~18h after.
      - No active typhoon: fall back to the model's flat 36h forecast horizon.
    """
    if hours_to_landfall is not None and 0 < hours_to_landfall < 120:
        window_start = max(hours_to_landfall, 0)
        return {
            "expected_onset_hrs": round(window_start, 1),
            "expected_peak_hrs":  round(window_start + 9, 1),
            "expected_end_hrs":   round(window_start + 18, 1),
        }
    return {"expected_onset_hrs": 0.0, "expected_peak_hrs": 18.0, "expected_end_hrs": 36.0}
