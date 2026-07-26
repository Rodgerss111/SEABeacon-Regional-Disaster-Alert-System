"""
SEABeacon — Component A: Flood LSTM
inference.py

Core per-basin inference logic. One function handles BOTH live and demo
mode — the only difference is where the raw discharge/rain/soil_moisture
values come from (live API fetch vs. pre-existing Supabase history).
"""

from datetime import datetime, timezone, timedelta

import numpy as np

import config
import db
import features as feat


def infer_basin(basin: dict, model, scaler_params: dict, feature_cols: list,
                typhoon_nodes: list, storm_name: str,
                fresh_row: dict = None, reference_time: datetime = None) -> dict | None:
    """
    Runs one inference cycle for a single basin.

    Args:
      basin          : one row from basin_meta.csv (basin_id, lat, lon, flood_cms, ...)
      model          : loaded Keras model
      scaler_params  : normalization params keyed by basin_id
      feature_cols   : ordered list of feature column names
      typhoon_nodes  : list of forecast nodes from Component B (may be empty)
      storm_name     : name of the active storm, or None
      fresh_row      : LIVE MODE ONLY — dict with the latest discharge_cms,
                       precip_mm_3h, soil_moisture to upsert before inferring.
                       Pass None in demo mode (history is already seeded).
      reference_time : DEMO MODE ONLY — fixed "current time" anchor.
                       Pass None in live mode (uses real wall-clock time).

    Returns the result dict (team-leader JSON schema), or None if there
    isn't yet enough history to fill the model's lookback window.
    """
    bid = basin["basin_id"]
    now = reference_time or datetime.now(timezone.utc)

    typhoon_feats = feat.nearest_typhoon_to_basin(
        basin, typhoon_nodes,
        radius_km=config.TYPHOON_RADIUS_KM.get(bid, 500),
        reference_time=reference_time,
    )

    # ── LIVE MODE: write the freshly-fetched row before reading history ────
    if fresh_row is not None:
        fresh_row = dict(fresh_row)
        fresh_row["typhoon_dist_km"]  = typhoon_feats["typhoon_dist_km"]
        fresh_row["typhoon_wind_kmh"] = typhoon_feats["typhoon_wind_kmh"]
        fresh_row["typhoon_name"]     = storm_name if typhoon_feats["typhoon_active"] else None
        db.write_raw(bid, fresh_row)

    hist_df = db.get_recent_window(bid, reference_time=reference_time)
    if hist_df.empty or len(hist_df) < config.SEQUENCE_LENGTH:
        print(
            f"    [{bid}] Not enough history: "
            f"{len(hist_df)}/{config.SEQUENCE_LENGTH} rows."
        )
        return None

    df_b = hist_df.tail(config.SEQUENCE_LENGTH).copy()
    df_b["soil_moisture"] = (
        df_b["soil_moisture"].ffill().fillna(0.3) if "soil_moisture" in df_b.columns else 0.3
    )
    df_b["typhoon_active"]    = typhoon_feats["typhoon_active"]
    df_b["typhoon_category"]  = typhoon_feats["typhoon_category"]
    df_b["hours_to_landfall"] = typhoon_feats["hours_to_landfall"]
    df_b = feat.engineer_features(df_b, basin)

    scaler = scaler_params.get(bid)
    if scaler is None:
        print(f"    [{bid}] No scaler params for this basin — skipping.")
        return None

    fc_avail = [c for c in feature_cols if c in df_b.columns]
    for col in fc_avail:
        idx = feature_cols.index(col)
        df_b[col] = (df_b[col].values - scaler["mean_"][idx]) / scaler["scale_"][idx]

    seq = df_b[fc_avail].values[-config.SEQUENCE_LENGTH:].astype(np.float32)
    if seq.shape[0] < config.SEQUENCE_LENGTH:
        return None
    X = seq.reshape(1, config.SEQUENCE_LENGTH, len(fc_avail))

    preds = model.predict(X, verbose=0)
    if not isinstance(preds, (list, tuple)):
        preds = [preds]

    flood_prob = float(np.clip(preds[0][0, 0], 0.01, 0.99))
    tier_code  = int(np.argmax(preds[1][0]))
    severity   = config.TIER_NAMES[tier_code].upper()

    last_discharge = float(hist_df["discharge_cms"].iloc[-1])
    arrival = feat.estimate_flood_arrival(typhoon_feats.get("hours_to_landfall"))
    expires = (now + timedelta(hours=36)).strftime("%Y-%m-%dT%H:%M:%SZ")

    result = {
        "province":    basin["provinces"][0],
        "country":     basin["country"],
        "score_type":  "physical_flood",
        "score_value": round(flood_prob, 4),
        "expires_at":  expires,
        "context": {
            "basin_name":           bid.replace("_", " ").title(),
            "discharge_cms":        round(last_discharge, 2),
            "threshold_cms":        round(basin["flood_cms"], 4),
            "forecast_horizon_hrs": 36,
            "severity_label":       severity,
            "affected_provinces":   basin["provinces"],
            "expected_onset_hrs":   arrival["expected_onset_hrs"],
            "expected_peak_hrs":    arrival["expected_peak_hrs"],
            "expected_end_hrs":     arrival["expected_end_hrs"],
            "typhoon_name":         storm_name if typhoon_feats["typhoon_active"] else None,
        },
    }
    if typhoon_feats["typhoon_active"]:
        result["context"].update({
            "typhoon_dist_km":   typhoon_feats["typhoon_dist_km"],
            "typhoon_wind_kmh":  typhoon_feats["typhoon_wind_kmh"],
            "typhoon_category":  int(typhoon_feats["typhoon_category"]),
            "hours_to_landfall": typhoon_feats["hours_to_landfall"],
        })
    return result
