"""
SEABeacon — Component A: Flood LSTM
demo_run.py

DEMO MODE — runs ONE inference cycle against the backfilled Karding/Noru
scenario (see demo_seed.py) and the fixed historical typhoon replay from
Component B. Intended for showing judges a working, reproducible demo
rather than waiting for a real typhoon during the presentation.

Run demo_seed.py first, then run this:
    python demo_seed.py
    python demo_run.py
"""

import json
from datetime import datetime, timezone

import db
import model_loader
import inference
import typhoon_client

# ── Fixed demo configuration ────────────────────────────────────────────────
# The exact simulation_run_id AND storm_name Component B used for their
# Karding/Noru historical replay. Both are filtered on together so this
# demo can never accidentally latch onto a different storm that happens
# to share a run_id (this was the cause of the earlier "SANVU" mix-up).
DEMO_SIMULATION_RUN_ID = "historical-backtest-2023"   # <-- confirm with Component B owner
DEMO_STORM_NAME        = "Super Typhoon Noru (Karding)"  # <-- exact string in their DB

# Pretend "now" for the demo — set to a point in the Karding timeline so
# hours_to_landfall comes out as a sensible positive countdown instead of
# a huge negative number (which happens if compared against today's real date).
DEMO_CURRENT_TIME = datetime(2022, 9, 25, 6, 0, 0, tzinfo=timezone.utc)


def main():
    print("=" * 70)
    print("SEABeacon Component A — DEMO MODE (Bagyong Karding / Noru Replay)")
    print(f'Demo "current time" anchor: {DEMO_CURRENT_TIME.isoformat()}')
    print("=" * 70)

    model, scaler_params, feature_cols, basins = model_loader.load_artifacts()

    print("\nFetching Karding/Noru demo typhoon scenario from Component B...")
    typhoon_nodes, storm_name = typhoon_client.fetch_demo_typhoon_forecast(
        simulation_run_id=DEMO_SIMULATION_RUN_ID,
        storm_name_target=DEMO_STORM_NAME,
        reference_time=DEMO_CURRENT_TIME,
    )

    print("\nRunning demo inference for all basins...")
    all_outputs = []
    for basin in basins:
        result = inference.infer_basin(
            basin, model, scaler_params, feature_cols,
            typhoon_nodes, storm_name,
            fresh_row=None,                    # demo mode: history already seeded
            reference_time=DEMO_CURRENT_TIME,  # demo mode: fixed timeline anchor
        )
        if result:
            all_outputs.append(result)
            ctx = result["context"]
            print(
                f'  [{basin["basin_id"]}] score={result["score_value"]} | '
                f'{ctx["severity_label"]} | onset +{ctx["expected_onset_hrs"]}h'
            )
            if ctx.get("typhoon_name"):
                print(f'    Storm: {ctx["typhoon_name"]}')

    if all_outputs:
        db.write_predictions(all_outputs, cleanup=False)
        print("\nDemo JSON output:")
        print(json.dumps(all_outputs, indent=2))
    else:
        print("\nNo outputs produced — did you run demo_seed.py first?")

    print("\nDemo cycle complete.")


if __name__ == "__main__":
    main()
