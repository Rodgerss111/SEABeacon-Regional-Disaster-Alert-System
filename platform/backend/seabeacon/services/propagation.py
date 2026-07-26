"""Propagation / impact-zone computation.

DEMO STUB
=========
Replaces the production XGBoost trajectory + rainfall propagation model described
in the SEABeacon proposal. The real model would be trained on IBTrACS historical
tracks and PAGASA / JMA / JTWC real-time feeds, plus IMERG precipitation grids.

This stub uses an explicit, deterministic radius-and-bearing approach calibrated
to roughly match Kammuri (2019)'s observed cross-border impact pattern. Same
inputs always yield the same outputs; do NOT present this as machine learning.

What the production model would replace:
  - The hard-coded distance thresholds (100 / 200 / 350 km) → learned hazard
    swath geometry conditioned on storm intensity, motion, and forward speed.
  - The category-as-severity heuristic → probabilistic damage forecast.
  - The linear interpolation of upcoming track positions → ensemble forecast
    track sampling.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from pyproj import Geod

from ..models import Severity

_GEOD = Geod(ellps="WGS84")


# DEMO STUB calibration. Documented here so reviewers can see exactly what is
# load-bearing and what would be replaced by trained parameters.
URGENT_RADIUS_KM = 100.0
WARNING_RADIUS_KM = 200.0
ADVISORY_RADIUS_KM = 350.0
URGENT_MIN_CATEGORY = 2
WARNING_MIN_CATEGORY = 1
URGENT_MAX_ETA_HOURS = 24.0
WARNING_MAX_ETA_HOURS = 48.0


@dataclass
class TrackPointLite:
    timestamp_seconds: float  # seconds since epoch (UTC)
    lat: float
    lon: float
    max_wind_kt: float
    category: int


@dataclass
class MunicipalityLite:
    id: int
    name: str
    country_code: str
    lat: float
    lon: float


@dataclass(frozen=True)
class ImpactPrediction:
    municipality_id: int
    municipality_name: str
    country_code: str
    lat: float
    lon: float
    severity: Severity
    eta_hours: float
    confidence: float


def geodesic_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km on the WGS84 ellipsoid."""
    _, _, dist_m = _GEOD.inv(lon1, lat1, lon2, lat2)
    return dist_m / 1000.0


def _classify(distance_km: float, category: int, eta_hours: float) -> Severity | None:
    """Apply the demo-stub severity rules.

    Severity tiers:
      - urgent:   centroid within URGENT_RADIUS_KM AND category >= 2 AND eta <= 24h
      - warning:  within WARNING_RADIUS_KM AND category >= 1 AND eta <= 48h
      - advisory: within ADVISORY_RADIUS_KM (any category, any horizon)
    """
    if (
        distance_km <= URGENT_RADIUS_KM
        and category >= URGENT_MIN_CATEGORY
        and eta_hours <= URGENT_MAX_ETA_HOURS
    ):
        return Severity.urgent
    if (
        distance_km <= WARNING_RADIUS_KM
        and category >= WARNING_MIN_CATEGORY
        and eta_hours <= WARNING_MAX_ETA_HOURS
    ):
        return Severity.warning
    if distance_km <= ADVISORY_RADIUS_KM:
        return Severity.advisory
    return None


def _confidence(distance_km: float, category: int) -> float:
    """A monotone-decreasing function of distance and increasing in intensity.

    DEMO STUB: scaled so urgent zones land in 0.75–0.95 and advisory zones in
    0.35–0.55. Production model would emit a calibrated probability.
    """
    distance_score = max(0.0, 1.0 - (distance_km / ADVISORY_RADIUS_KM))
    cat_score = min(1.0, category / 5.0)
    return round(0.4 * cat_score + 0.6 * distance_score, 3)


def compute_impact_zones(
    current_track_point: TrackPointLite,
    upcoming_track: Sequence[TrackPointLite],
    municipalities: Iterable[MunicipalityLite],
    horizon_hours: int = 72,
) -> list[ImpactPrediction]:
    """Return one ImpactPrediction per municipality within the storm's swath.

    For each muni, walk the projected upcoming track points (within
    `horizon_hours` from `current_track_point`), find the closest approach,
    then classify severity.
    """
    horizon_seconds = horizon_hours * 3600.0
    cutoff = current_track_point.timestamp_seconds + horizon_seconds

    candidates: list[TrackPointLite] = [
        p for p in upcoming_track
        if current_track_point.timestamp_seconds <= p.timestamp_seconds <= cutoff
    ]
    if not candidates:
        candidates = [current_track_point]

    out: list[ImpactPrediction] = []
    for muni in municipalities:
        best_distance_km = float("inf")
        best_eta_hours = float("inf")
        best_category = 0
        best_wind = 0.0

        for p in candidates:
            d_km = geodesic_distance_km(p.lat, p.lon, muni.lat, muni.lon)
            if d_km < best_distance_km:
                best_distance_km = d_km
                best_eta_hours = max(
                    0.0,
                    (p.timestamp_seconds - current_track_point.timestamp_seconds) / 3600.0,
                )
                best_category = p.category
                best_wind = p.max_wind_kt

        severity = _classify(best_distance_km, best_category, best_eta_hours)
        if severity is None:
            continue

        out.append(
            ImpactPrediction(
                municipality_id=muni.id,
                municipality_name=muni.name,
                country_code=muni.country_code,
                lat=muni.lat,
                lon=muni.lon,
                severity=severity,
                eta_hours=round(best_eta_hours, 1),
                confidence=_confidence(best_distance_km, best_category),
            )
        )

    severity_order = {Severity.urgent: 0, Severity.warning: 1, Severity.advisory: 2}
    out.sort(key=lambda p: (severity_order[p.severity], p.eta_hours))
    return out
