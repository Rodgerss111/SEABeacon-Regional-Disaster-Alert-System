"""
SEABeacon — Component A: Flood LSTM
main.py

LIVE MODE — continuous polling daemon. Fetches real-time rainfall, river
discharge, and soil moisture from Open-Meteo, fetches the latest typhoon
forecast from Component B, runs the LSTM, and writes results to Supabase.
Runs forever, sleeping between cycles.

Usage:
    python main.py
"""

import time
from datetime import datetime, timezone

import config
import db
import model_loader
import inference
import live_data
import typhoon_client

POLL_INTERVAL_SECONDS = 60 * 60  # 1 hour between cycles

SEVERITY_ICON = {"WARNING": "[!!]", "ADVISORY": "[!]", "WATCH": "[~]", "NORMAL": "[ok]"}


def fetch_fresh_row(basin: dict, now_utc: datetime) -> dict:
    """Pulls live sensor values for one basin, with graceful fallbacks."""
    discharge = live_data.fetch_live_discharge(basin["lat"], basin["lon"])
    rain_mm   = live_data.fetch_live_rainfall(basin["lat"], basin["lon"])
    soil_m    = live_data.fetch_live_soil_moisture(basin["lat"], basin["lon"])

    hist_short = db.get_recent_window(basin["basin_id"], lookback_days=1)

    def fallback(val, col, default):
        if val is not None:
            return val
        fb = (
            float(hist_short[col].iloc[-1])
            if not hist_short.empty and col in hist_short
            else default
        )
        print(f"    {col}: using fallback ({fb})")
        return fb

    return {
        "timestamp_utc": now_utc.isoformat(),
        "basin_id":      basin["basin_id"],
        "discharge_cms": round(fallback(discharge, "discharge_cms", 0.0), 4),
        "precip_mm_3h":  round(fallback(rain_mm,   "precip_mm_3h",  0.0), 4),
        "soil_moisture": round(fallback(soil_m,    "soil_moisture", 0.3), 4),
    }


def run_daemon():
    print("==================================================")
    print("   SEABeacon Component A Daemon (Flood LSTM)      ")
    print("==================================================\n")

    state = db.load_last_state()
    print(f"--> [Daemon] 1. Last Run: {state.get('last_run_timestamp') or 'First Run'}")

    print("\n--> [Daemon] 2. Loading model...")
    model, scaler_params, feature_cols, basins = model_loader.load_artifacts()

    print("\n--> [Daemon] 3. Fetching typhoon forecast from Component B...")
    typhoon_nodes, typhoon_run_id, storm_name = typhoon_client.fetch_typhoon_forecast()

    is_new = typhoon_run_id != state.get("last_typhoon_run_id")
    if is_new and typhoon_run_id:
        print(f"  NEW TYPHOON DATA: {storm_name or typhoon_run_id}")
    else:
        print("  No change in typhoon data since last run.")

    print("\n--> [Daemon] 4. Running inference for all basins...")
    now_utc = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    now_utc = now_utc.replace(hour=(now_utc.hour // 3) * 3)

    all_outputs = []
    for basin in basins:
        print(f"  [{basin['basin_id']}]")
        fresh_row = fetch_fresh_row(basin, now_utc)
        result = inference.infer_basin(
            basin, model, scaler_params, feature_cols,
            typhoon_nodes, storm_name,
            fresh_row=fresh_row, reference_time=None,  # live mode: real wall-clock time
        )
        if result:
            all_outputs.append(result)
            print(f"    -> {result['score_value']} | {result['context']['severity_label']}")
        db.cleanup_old_raw(basin["basin_id"])

    if all_outputs:
        db.write_predictions(all_outputs)
        print("\n" + "=" * 60)
        print("SEABeacon Flood Risk Summary")
        print("=" * 60)
        for r in sorted(all_outputs, key=lambda x: x["score_value"], reverse=True):
            ctx  = r["context"]
            sev  = ctx["severity_label"]
            icon = SEVERITY_ICON.get(sev, "[?]")
            print(f"\n{icon} {ctx['basin_name']} ({r['country']}) "
                  f"{r['score_value'] * 100:.1f}% | {sev}")
            print(f"   Discharge   : {ctx['discharge_cms']:.2f} / {ctx['threshold_cms']:.2f} m3/s")
            print(f"   Flood window: onset +{ctx['expected_onset_hrs']}h | "
                  f"peak +{ctx['expected_peak_hrs']}h | clears +{ctx['expected_end_hrs']}h")
            if ctx.get("typhoon_name"):
                print(f"   Storm: {ctx['typhoon_name']} — "
                      f"{ctx.get('typhoon_dist_km', '?')}km away, "
                      f"{ctx.get('typhoon_wind_kmh', '?')}kph")
            print(f"   Provinces   : {', '.join(ctx['affected_provinces'])}")
        print("\n" + "=" * 60)
    else:
        print("\nNo predictions yet — still accumulating history rows.")

    db.save_state(datetime.now(timezone.utc).isoformat(), typhoon_run_id)
    print("\n[Daemon] Cycle complete.\n")


def main():
    print(f"Starting SEABeacon Component A continuous polling "
          f"({POLL_INTERVAL_SECONDS // 3600}-hour interval)...")
    while True:
        try:
            run_daemon()
        except Exception as e:
            print(f"[Daemon] Cycle error: {e} — retrying next cycle.")
        print(f"Sleeping {POLL_INTERVAL_SECONDS // 3600}h until next cycle...")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
