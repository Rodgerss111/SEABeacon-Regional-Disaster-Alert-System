"""Idempotent fixture loader. Run with `python -m seabeacon.seed`."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .config import FIXTURES_DIR
from .db import init_db, session_scope
from .models import (
    Country,
    HazardType,
    Municipality,
    Scenario,
    Signal,
    TrackPoint,
    Classification,
)


def _parse_iso(s: str) -> datetime:
    # Stored as naive UTC for SQLite simplicity.
    return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)


def load_fixture(name: str) -> dict:
    path: Path = FIXTURES_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


def seed_countries_and_munis(session) -> None:
    data = load_fixture("asean_admin.geojson")

    for c in data["countries"]:
        if not session.get(Country, c["code"]):
            session.add(Country(**c))
    session.flush()

    existing_munis = {(m.country_code, m.name) for m in session.query(Municipality).all()}
    for m in data["municipalities"]:
        key = (m["country_code"], m["name"])
        if key in existing_munis:
            continue
        session.add(
            Municipality(
                country_code=m["country_code"],
                name=m["name"],
                lat=m["lat"],
                lon=m["lon"],
                population=m.get("population", 0),
                geom_geojson=None,
            )
        )


def seed_kammuri(session) -> None:
    track_data = load_fixture("kammuri_track.json")
    signals_data = load_fixture("kammuri_signals.json")

    points = track_data["points"]
    start = _parse_iso(points[0]["timestamp_utc"])
    end = _parse_iso(points[-1]["timestamp_utc"])

    scenario = session.query(Scenario).filter_by(slug="kammuri-2019").one_or_none()
    if scenario is None:
        scenario = Scenario(
            slug="kammuri-2019",
            name="Typhoon Kammuri (Tisoy) — December 2019",
            hazard_type=HazardType.typhoon,
            start_time=start,
            end_time=end,
            description=(
                "Replay of Typhoon Kammuri (locally Tisoy) which made landfall in Sorsogon, "
                "Philippines on 2 December 2019, traversed Luzon, exited into the South China "
                "Sea, and degraded into a tropical depression as it approached the central "
                "Vietnam coast on 5–6 December."
            ),
        )
        session.add(scenario)
        session.flush()

    if not scenario.track_points:
        for p in points:
            session.add(
                TrackPoint(
                    scenario_id=scenario.id,
                    timestamp=_parse_iso(p["timestamp_utc"]),
                    lat=p["lat"],
                    lon=p["lon"],
                    max_wind_kt=p["max_wind_kt"],
                    pressure_mb=p["pressure_mb"],
                    category=p["category"],
                )
            )

    if not scenario.signals:
        for s in signals_data["signals"]:
            session.add(
                Signal(
                    scenario_id=scenario.id,
                    timestamp=_parse_iso(s["timestamp_utc"]),
                    lat=s["lat"],
                    lon=s["lon"],
                    language=s["language"],
                    source_type=s["source_type"],
                    text=s["text"],
                    classification=Classification(s["classification"]),
                    confidence=s["confidence"],
                )
            )


def seed_all() -> None:
    init_db()
    with session_scope() as session:
        seed_countries_and_munis(session)
        seed_kammuri(session)
    print("[seed] OK — countries, municipalities, scenario, track, signals loaded.")


if __name__ == "__main__":
    seed_all()
