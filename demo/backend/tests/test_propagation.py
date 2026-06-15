from __future__ import annotations

from datetime import datetime, timezone

from seabeacon.models import Severity
from seabeacon.services.propagation import (
    MunicipalityLite,
    TrackPointLite,
    compute_impact_zones,
    geodesic_distance_km,
)


def _ts(year, month, day, hour=0) -> float:
    return datetime(year, month, day, hour, tzinfo=timezone.utc).timestamp()


MANILA = MunicipalityLite(id=1, name="Manila", country_code="PH", lat=14.599, lon=120.984)
DA_NANG = MunicipalityLite(id=2, name="Da Nang", country_code="VN", lat=16.054, lon=108.222)
BANGKOK = MunicipalityLite(id=3, name="Bangkok", country_code="TH", lat=13.756, lon=100.502)
SINGAPORE = MunicipalityLite(id=4, name="Singapore", country_code="SG", lat=1.290, lon=103.851)


def test_distance_helper_sanity():
    d = geodesic_distance_km(14.6, 121.0, 14.6, 121.0)
    assert d == 0.0
    d2 = geodesic_distance_km(14.6, 121.0, 14.6, 122.0)
    assert 100 < d2 < 115  # ~1 deg lon at this latitude


def test_manila_urgent_when_storm_within_50km():
    """Manila is `urgent` when a Cat-3 track point is within 50 km."""
    now = _ts(2019, 12, 3, 12)
    current = TrackPointLite(timestamp_seconds=now, lat=14.5, lon=121.3, max_wind_kt=100, category=3)
    upcoming = [
        TrackPointLite(timestamp_seconds=now + 6 * 3600, lat=14.6, lon=121.0, max_wind_kt=95, category=3),
    ]
    preds = compute_impact_zones(current, upcoming, [MANILA])
    assert len(preds) == 1
    assert preds[0].severity == Severity.urgent
    assert preds[0].municipality_name == "Manila"


def test_da_nang_warning_48h_before_vn_landfall():
    """Da Nang receives at least a `warning` 48h before track approaches VN coast."""
    now = _ts(2019, 12, 4, 0)
    current = TrackPointLite(timestamp_seconds=now, lat=14.0, lon=119.0, max_wind_kt=55, category=0)
    upcoming = [
        TrackPointLite(timestamp_seconds=now + 24 * 3600, lat=14.9, lon=113.6, max_wind_kt=35, category=0),
        TrackPointLite(timestamp_seconds=now + 42 * 3600, lat=15.5, lon=110.2, max_wind_kt=40, category=1),
        TrackPointLite(timestamp_seconds=now + 48 * 3600, lat=15.9, lon=108.8, max_wind_kt=45, category=1),
    ]
    preds = compute_impact_zones(current, upcoming, [DA_NANG])
    assert len(preds) == 1
    assert preds[0].severity in (Severity.warning, Severity.urgent)
    assert preds[0].country_code == "VN"


def test_far_muni_never_alerts():
    """A municipality 800+ km from any track point produces no prediction."""
    now = _ts(2019, 12, 2, 0)
    current = TrackPointLite(timestamp_seconds=now, lat=13.5, lon=124.3, max_wind_kt=120, category=4)
    upcoming = [
        TrackPointLite(timestamp_seconds=now + 6 * 3600, lat=13.5, lon=124.0, max_wind_kt=120, category=4),
        TrackPointLite(timestamp_seconds=now + 12 * 3600, lat=13.6, lon=123.5, max_wind_kt=115, category=4),
    ]
    preds = compute_impact_zones(current, upcoming, [SINGAPORE])
    assert preds == []


def test_classification_orders_urgent_first():
    now = _ts(2019, 12, 2, 0)
    current = TrackPointLite(timestamp_seconds=now, lat=13.0, lon=124.0, max_wind_kt=120, category=4)
    upcoming = [
        TrackPointLite(timestamp_seconds=now + 3 * 3600, lat=13.1, lon=124.0, max_wind_kt=120, category=4),
    ]
    preds = compute_impact_zones(current, upcoming, [MANILA, BANGKOK])
    severities = [p.severity for p in preds]
    if severities:
        for prev, nxt in zip(severities, severities[1:]):
            order = {Severity.urgent: 0, Severity.warning: 1, Severity.advisory: 2}
            assert order[prev] <= order[nxt]
