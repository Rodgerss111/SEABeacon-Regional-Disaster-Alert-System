from __future__ import annotations

from datetime import datetime, timedelta

from seabeacon.models import TrackPoint
from seabeacon.services.scenario_clock import _interp_track_point


def _tp(ts: datetime, lat: float, lon: float, wind: float = 50, pressure: float = 990, cat: int = 1):
    return TrackPoint(
        scenario_id=1,
        timestamp=ts,
        lat=lat,
        lon=lon,
        max_wind_kt=wind,
        pressure_mb=pressure,
        category=cat,
    )


def test_interpolates_midpoint():
    t0 = datetime(2019, 12, 1, 0, 0, 0)
    t1 = t0 + timedelta(hours=6)
    track = [_tp(t0, 13.0, 124.0), _tp(t1, 13.6, 124.6)]
    midpoint = _interp_track_point(track, t0 + timedelta(hours=3))
    assert abs(midpoint.lat - 13.3) < 1e-6
    assert abs(midpoint.lon - 124.3) < 1e-6


def test_clamps_to_bounds():
    t0 = datetime(2019, 12, 1, 0, 0, 0)
    t1 = t0 + timedelta(hours=6)
    track = [_tp(t0, 13.0, 124.0), _tp(t1, 13.6, 124.6)]
    before = _interp_track_point(track, t0 - timedelta(hours=1))
    after = _interp_track_point(track, t1 + timedelta(hours=1))
    assert (before.lat, before.lon) == (13.0, 124.0)
    assert (after.lat, after.lon) == (13.6, 124.6)
