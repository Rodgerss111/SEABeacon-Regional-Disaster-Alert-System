"""
SEABeacon — Component A: Flood LSTM
demo_seed.py

BACKFILL SCRIPT — run this ONCE before demo_run.py to seed 55 historical
rows per basin simulating Super Typhoon Noru (Bagyong Karding), so the
56-step lookback window has enough history for the model to run on.

  Landfall: Sept 25, 2022, Burdeos/Dingalan, Luzon, Philippines

Usage:
    python demo_seed.py
"""

import numpy as np
from datetime import datetime, timezone, timedelta

import db

STORM_NAME = "Bagyong Karding (Noru)"

# (base_discharge, peak_discharge, base_rain_3h, peak_rain_3h, ...)
# Luzon basins are hit hardest; Noru exits PAR by Sept 27.
BASIN_PROFILES = {
    "PH_LUZON_NORTH": {
        "base_dis": 350.0, "peak_dis": 2800.0,
        "base_rain": 4.0,  "peak_rain": 68.0,
        "peak_step": 38,   "spread": 8,
        "typhoon_active": True, "wind_kmh": 195.0, "dist_km": 120.0,
    },
    "PH_LUZON_CENTRAL": {
        "base_dis": 280.0, "peak_dis": 3200.0,
        "base_rain": 5.0,  "peak_rain": 82.0,
        "peak_step": 40,   "spread": 10,
        "typhoon_active": True, "wind_kmh": 185.0, "dist_km": 80.0,
    },
    "PH_VISAYAS": {
        "base_dis": 120.0, "peak_dis": 480.0,
        "base_rain": 3.0,  "peak_rain": 22.0,
        "peak_step": 35,   "spread": 6,
        "typhoon_active": True, "wind_kmh": 95.0, "dist_km": 380.0,
    },
    "PH_MINDANAO": {
        "base_dis": 200.0, "peak_dis": 310.0,
        "base_rain": 2.0,  "peak_rain": 8.0,
        "peak_step": 30,   "spread": 5,
        "typhoon_active": False, "wind_kmh": 0.0, "dist_km": 500.0,
    },
    "VN_CENTRAL": {
        "base_dis": 180.0, "peak_dis": 950.0,
        "base_rain": 3.5,  "peak_rain": 38.0,
        "peak_step": 45,   "spread": 7,
        "typhoon_active": True, "wind_kmh": 155.0, "dist_km": 210.0,
    },
    "VN_MEKONG": {
        "base_dis": 4500.0, "peak_dis": 6200.0,
        "base_rain": 4.0,   "peak_rain": 18.0,
        "peak_step": 47,    "spread": 6,
        "typhoon_active": False, "wind_kmh": 0.0, "dist_km": 600.0,
    },
    "TH_CHAOPHRAYA": {
        "base_dis": 320.0, "peak_dis": 520.0,
        "base_rain": 2.0,  "peak_rain": 10.0,
        "peak_step": 50,   "spread": 5,
        "typhoon_active": False, "wind_kmh": 0.0, "dist_km": 800.0,
    },
}


def generate_noru_backfill() -> list:
    now_utc = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    now_utc = now_utc.replace(hour=(now_utc.hour // 3) * 3)

    # 55 steps back (3h each), leaving step 56 free for a live/demo fetch
    timestamps = [now_utc - timedelta(hours=3 * i) for i in range(56, 0, -1)]

    rows = []
    rng = np.random.default_rng(seed=2022)  # reproducible across reruns

    for basin_id, p in BASIN_PROFILES.items():
        for step, ts in enumerate(timestamps):
            pulse = np.exp(-0.5 * ((step - p["peak_step"]) / p["spread"]) ** 2)

            discharge = p["base_dis"] + (p["peak_dis"] - p["base_dis"]) * pulse
            rain      = p["base_rain"] + (p["peak_rain"] - p["base_rain"]) * pulse
            soil_m    = 0.30 + (0.48 - 0.30) * pulse

            discharge += rng.normal(0, discharge * 0.03)
            rain      += rng.normal(0, max(rain * 0.05, 0.1))
            soil_m    += rng.normal(0, 0.02)

            discharge = max(round(float(discharge), 4), 0.0)
            rain      = max(round(float(rain), 4), 0.0)
            soil_m    = max(round(float(soil_m), 4), 0.0)

            typhoon_active = 1.0 if (p["typhoon_active"] and step >= p["peak_step"] - 12) else 0.0
            wind_kmh = round(p["wind_kmh"] * pulse, 1) if typhoon_active else 0.0
            dist_km  = round(p["dist_km"] + (500 - p["dist_km"]) * (1 - pulse), 1)

            rows.append({
                "timestamp_utc":    ts.isoformat(),
                "basin_id":         basin_id,
                "discharge_cms":    discharge,
                "precip_mm_3h":     rain,
                "soil_moisture":    soil_m,
                "typhoon_dist_km":  dist_km,
                "typhoon_wind_kmh": wind_kmh,
                "typhoon_name":     STORM_NAME if typhoon_active else None,
            })

    return rows


def main():
    print("Generating Noru/Karding backfill rows...")
    rows = generate_noru_backfill()
    print(f"Total rows to insert: {len(rows)} ({len(rows) // len(BASIN_PROFILES)} per basin)")

    print("Upserting to Supabase flood_raw_operational...")
    db.write_raw_batch(rows)

    print("Backfill complete. Now run: python demo_run.py")


if __name__ == "__main__":
    main()
