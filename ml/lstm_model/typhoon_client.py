"""
SEABeacon — Component A: Flood LSTM
typhoon_client.py

Fetches typhoon forecast nodes from Component B's Supabase project
(read-only, via their anon key). Two entry points:
  - fetch_typhoon_forecast()      -> live mode, latest active run
  - fetch_demo_typhoon_forecast() -> demo mode, fixed historical run_id
"""

import requests

import config
import db


def _headers() -> dict:
    return {
        "apikey": config.COMPONENT_B_ANON_KEY,
        "Authorization": f"Bearer {config.COMPONENT_B_ANON_KEY}",
        "Content-Type": "application/json",
    }


def fetch_typhoon_forecast():
    """
    LIVE MODE — fetches whichever simulation_run_id Component B most
    recently created. Returns (nodes, run_id, storm_name). Never raises;
    returns empty results on any failure so Component A keeps running.
    """
    if not config.COMPONENT_B_ANON_KEY:
        print("  No COMPONENT_B_ANON_KEY — skipping typhoon fetch.")
        return [], None, None

    try:
        r = requests.get(
            config.COMPONENT_B_URL, headers=_headers(),
            params={"select": "simulation_run_id", "order": "created_at.desc", "limit": 1},
        )
        r.raise_for_status()
        data = r.json()
        if not data:
            print("  Component B DB empty — no active typhoon.")
            return [], None, None
        run_id = data[0]["simulation_run_id"]
    except Exception as e:
        print(f"  Could not reach Component B: {e}")
        return [], None, None

    nodes, storm_name = _fetch_nodes_for_run(run_id)
    if nodes is None:
        print("  Could not fetch typhoon nodes.")
        return [], run_id, None

    print(f"  Fetched {len(nodes)} typhoon nodes (run {run_id})")
    if storm_name:
        print(f"  Storm: {storm_name}")

    db.log_component_b_fetch(nodes, run_id)
    return nodes, run_id, storm_name


def fetch_demo_typhoon_forecast(simulation_run_id: str, storm_name_target: str,
                                reference_time=None):
    """
    DEMO MODE — fetches a FIXED, known simulation_run_id from Component B
    (e.g. their Karding/Noru historical replay), filtered also by the exact
    storm_name so you never accidentally pull a different storm that
    happens to share a run_id (this was the SANVU mix-up bug — fixed here
    by always filtering on storm_name explicitly).

    Returns (nodes, storm_name).
    """
    storm_name = storm_name_target
    nodes, storm_name = _fetch_nodes_for_run(
        simulation_run_id, storm_name_filter=storm_name_target
    )
    nodes = nodes or []
    print(f'  Fetched {len(nodes)} nodes from demo scenario "{simulation_run_id}"')
    print(f"  Storm name: {storm_name or storm_name_target}")

    db.log_component_b_fetch(nodes, simulation_run_id, fetched_at=reference_time)
    return nodes, storm_name or storm_name_target


def _fetch_nodes_for_run(run_id: str, storm_name_filter: str = None):
    """Internal helper — tries with storm_name column, falls back without it."""
    nodes, storm_name = None, None
    for cols in (
        "forecast_target_time,predicted_lat,predicted_lon,predicted_wind_kph,storm_name",
        "forecast_target_time,predicted_lat,predicted_lon,predicted_wind_kph",
    ):
        params = {
            "select": cols,
            "simulation_run_id": f"eq.{run_id}",
            "order": "forecast_target_time.asc",
        }
        if storm_name_filter:
            params["storm_name"] = f"eq.{storm_name_filter}"

        try:
            r = requests.get(config.COMPONENT_B_URL, headers=_headers(), params=params)
            if r.status_code == 200:
                nodes = r.json()
                if nodes and "storm_name" in nodes[0]:
                    storm_name = nodes[0]["storm_name"]
                break
        except Exception:
            continue

    return nodes, storm_name
