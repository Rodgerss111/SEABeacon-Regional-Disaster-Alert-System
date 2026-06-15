"""Scenario clock — drives the entire demo replay.

A single asyncio task per scenario advances scenario time at a configurable
speed (scenario seconds per real second). At each tick (every 30 scenario
minutes) it:

  1. Interpolates the current track position from stored TrackPoints.
  2. Calls propagation.compute_impact_zones to find newly-affected munis.
  3. Persists Alerts for any new (country, muni, severity) combos and
     dispatches them to Telegram subscribers.
  4. Surfaces any seeded Signals whose timestamp falls in the tick window.
  5. Pushes events into a per-scenario asyncio.Queue for SSE consumers.

Only one active run per scenario_slug at a time (demo doesn't need concurrency).

The runner also supports `seek(slug, target_time, resume=...)`: it computes the
deterministic state at any point in the scenario (no sleeps, no Telegram
dispatch) and optionally resumes the live clock from there.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Awaitable, Callable, Optional

from sqlalchemy import select

from ..db import SessionLocal
from ..models import (
    HazardType,
    Municipality,
    Scenario,
    Signal,
    TrackPoint,
)
from .alerting import create_alerts_for_prediction, dispatch_alert_to_subscribers
from .propagation import (
    ImpactPrediction,
    MunicipalityLite,
    TrackPointLite,
    compute_impact_zones,
)

logger = logging.getLogger("seabeacon.clock")

TICK_SCENARIO_MINUTES = 30
TICK_STEP = timedelta(minutes=TICK_SCENARIO_MINUTES)
SendMessage = Callable[[int, str], Awaitable[bool]]


def _interp_track_point(track: list[TrackPoint], now: datetime) -> TrackPoint:
    """Linearly interpolate the storm position at scenario-time `now`."""
    if now <= track[0].timestamp:
        return track[0]
    if now >= track[-1].timestamp:
        return track[-1]

    for a, b in zip(track, track[1:]):
        if a.timestamp <= now <= b.timestamp:
            span = (b.timestamp - a.timestamp).total_seconds()
            t = 0.0 if span == 0 else (now - a.timestamp).total_seconds() / span
            interp = TrackPoint(
                scenario_id=a.scenario_id,
                timestamp=now,
                lat=a.lat + (b.lat - a.lat) * t,
                lon=a.lon + (b.lon - a.lon) * t,
                max_wind_kt=a.max_wind_kt + (b.max_wind_kt - a.max_wind_kt) * t,
                pressure_mb=a.pressure_mb + (b.pressure_mb - a.pressure_mb) * t,
                category=a.category if t < 0.5 else b.category,
            )
            return interp
    return track[-1]


def _to_lite(p: TrackPoint) -> TrackPointLite:
    return TrackPointLite(
        timestamp_seconds=p.timestamp.replace(tzinfo=None).timestamp(),
        lat=p.lat,
        lon=p.lon,
        max_wind_kt=p.max_wind_kt,
        category=p.category,
    )


def _muni_to_lite(m: Municipality) -> MunicipalityLite:
    return MunicipalityLite(
        id=m.id, name=m.name, country_code=m.country_code, lat=m.lat, lon=m.lon
    )


def _serialize_event(event_type: str, payload: dict) -> dict:
    return {"event": event_type, "data": json.dumps(payload, default=str)}


def _track_to_dict(p: TrackPoint) -> dict:
    return {
        "timestamp": p.timestamp.isoformat(),
        "lat": p.lat,
        "lon": p.lon,
        "max_wind_kt": p.max_wind_kt,
        "pressure_mb": p.pressure_mb,
        "category": p.category,
    }


def _impact_to_dict(pred: ImpactPrediction) -> dict:
    return {
        "municipality_id": pred.municipality_id,
        "municipality_name": pred.municipality_name,
        "country_code": pred.country_code,
        "lat": pred.lat,
        "lon": pred.lon,
        "severity": pred.severity.value,
        "eta_hours": pred.eta_hours,
        "confidence": pred.confidence,
    }


def _signal_to_dict(s: Signal) -> dict:
    return {
        "id": s.id,
        "timestamp": s.timestamp.isoformat(),
        "lat": s.lat,
        "lon": s.lon,
        "language": s.language,
        "source_type": s.source_type,
        "text": s.text,
        "classification": s.classification.value,
        "confidence": s.confidence,
    }


@dataclass
class ScenarioRun:
    run_id: str
    scenario_slug: str
    speed: float
    started_at: datetime
    scenario_time: Optional[datetime] = None
    current_point: Optional[TrackPoint] = None
    track_so_far: list[dict] = field(default_factory=list)
    impact_zones: dict[tuple[int, str], dict] = field(default_factory=dict)
    alerts: list[dict] = field(default_factory=list)
    signals: list[dict] = field(default_factory=list)
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    task: Optional[asyncio.Task] = None
    stopped: bool = False


@dataclass
class _ScenarioCtx:
    scenario_id: int
    scenario_start: datetime
    scenario_end: datetime
    hazard_type: HazardType
    storm_name: str
    track: list[TrackPoint]
    track_lites: list[TrackPointLite]
    muni_lites: list[MunicipalityLite]
    seeded_signals: list[Signal]


def _load_ctx(slug: str) -> Optional[_ScenarioCtx]:
    with SessionLocal() as session:
        scenario = session.execute(
            select(Scenario).where(Scenario.slug == slug)
        ).scalar_one_or_none()
        if scenario is None:
            return None

        track = list(session.execute(
            select(TrackPoint)
            .where(TrackPoint.scenario_id == scenario.id)
            .order_by(TrackPoint.timestamp)
        ).scalars().all())
        munis = list(session.execute(select(Municipality)).scalars().all())
        seeded_signals = list(session.execute(
            select(Signal)
            .where(Signal.scenario_id == scenario.id)
            .order_by(Signal.timestamp)
        ).scalars().all())

        # Eagerly access scalar attrs while session is open; objects detach cleanly.
        for o in track + munis + seeded_signals:
            session.expunge(o)

        return _ScenarioCtx(
            scenario_id=scenario.id,
            scenario_start=scenario.start_time,
            scenario_end=scenario.end_time,
            hazard_type=scenario.hazard_type,
            storm_name=(
                scenario.name.split(" ")[1] if " " in scenario.name else "the storm"
            ),
            track=track,
            track_lites=[_to_lite(p) for p in track],
            muni_lites=[_muni_to_lite(m) for m in munis],
            seeded_signals=seeded_signals,
        )


async def _advance_one_tick(
    run: ScenarioRun,
    ctx: _ScenarioCtx,
    *,
    queue_events: bool,
    dispatch: bool,
    send_message: Optional[SendMessage],
) -> None:
    """Process the tick at run.scenario_time, then advance run.scenario_time
    by TICK_STEP. Idempotent against pre-populated state (track points,
    impact zones, alerts, signals are deduplicated)."""
    current = _interp_track_point(ctx.track, run.scenario_time)
    run.current_point = current

    current_iso = current.timestamp.isoformat()
    last_ts = run.track_so_far[-1]["timestamp"] if run.track_so_far else None
    if last_ts != current_iso:
        run.track_so_far.append(_track_to_dict(current))

    if queue_events:
        await run.queue.put(_serialize_event("tick", {
            "scenario_time": run.scenario_time.isoformat(),
            "current_point": _track_to_dict(current),
        }))

    current_lite = _to_lite(current)
    upcoming = [
        p for p in ctx.track_lites
        if p.timestamp_seconds >= current_lite.timestamp_seconds
    ]
    preds = compute_impact_zones(current_lite, upcoming, ctx.muni_lites, horizon_hours=72)

    new_predictions: list[ImpactPrediction] = []
    for pred in preds:
        key = (pred.municipality_id, pred.severity.value)
        if key in run.impact_zones:
            continue
        run.impact_zones[key] = _impact_to_dict(pred)
        new_predictions.append(pred)

    if new_predictions:
        # `new_predictions` are predictions whose (muni, severity) key was not
        # yet in run.impact_zones — i.e. ones this run is encountering for the
        # first time. We emit SSE/Telegram for every language alert under each
        # such prediction, regardless of whether the underlying DB row was
        # freshly created or already existed from a prior run. (For seek mode
        # both `queue_events` and `dispatch` are False, so neither fires.)
        with SessionLocal() as session:
            for pred in new_predictions:
                all_alerts, _new_alerts = create_alerts_for_prediction(
                    session,
                    scenario_id=ctx.scenario_id,
                    hazard_type=ctx.hazard_type,
                    storm_name=ctx.storm_name,
                    issued_at=run.scenario_time,
                    prediction=pred,
                )
                session.commit()
                for alert in all_alerts:
                    payload = {
                        "id": alert.id,
                        "scenario_id": alert.scenario_id,
                        "country_code": alert.country_code,
                        "municipality_id": alert.municipality_id,
                        "severity": alert.severity.value,
                        "issued_at": alert.issued_at.isoformat(),
                        "title": alert.title,
                        "body": alert.body,
                        "language": alert.language,
                        "lat": pred.lat,
                        "lon": pred.lon,
                        "municipality_name": pred.municipality_name,
                        "eta_hours": pred.eta_hours,
                        "confidence": pred.confidence,
                    }
                    run.alerts.append(payload)

                    if queue_events:
                        await run.queue.put(_serialize_event("alert", payload))

                    if dispatch and send_message is not None:
                        try:
                            await dispatch_alert_to_subscribers(
                                session, alert, send_message=send_message
                            )
                            session.commit()
                        except Exception as exc:  # noqa: BLE001
                            logger.warning("dispatch failed: %s", exc)
                            session.rollback()

    # Surface seeded signals in this tick window.
    surfaced = len(run.signals)
    tick_window_end = run.scenario_time + TICK_STEP
    while (
        surfaced < len(ctx.seeded_signals)
        and ctx.seeded_signals[surfaced].timestamp <= tick_window_end
    ):
        s = ctx.seeded_signals[surfaced]
        payload = _signal_to_dict(s)
        run.signals.append(payload)
        if queue_events:
            await run.queue.put(_serialize_event("signal", payload))
        surfaced += 1

    run.scenario_time += TICK_STEP


class ScenarioRunner:
    def __init__(self) -> None:
        self.runs: dict[str, ScenarioRun] = {}
        self._send_message: Optional[SendMessage] = None

    def attach_sender(self, send_message: SendMessage) -> None:
        self._send_message = send_message

    def get_active(self, slug: str) -> Optional[ScenarioRun]:
        run = self.runs.get(slug)
        if run and not run.stopped:
            return run
        return None

    def _new_run(self, slug: str, speed: float) -> ScenarioRun:
        return ScenarioRun(
            run_id=str(uuid.uuid4()),
            scenario_slug=slug,
            speed=max(1.0, speed),
            started_at=datetime.utcnow(),
        )

    async def start(self, slug: str, speed: float) -> ScenarioRun:
        if self.get_active(slug):
            await self.stop(slug)

        run = self._new_run(slug, speed)
        self.runs[slug] = run
        run.task = asyncio.create_task(self._run_loop(run), name=f"scenario:{slug}")
        return run

    async def stop(self, slug: str) -> None:
        run = self.runs.get(slug)
        if not run or run.stopped:
            return
        run.stopped = True
        if run.task:
            run.task.cancel()
            try:
                await run.task
            except (asyncio.CancelledError, Exception):
                pass
        await run.queue.put({"event": "done", "data": json.dumps({"reason": "stopped"})})

    async def seek(
        self,
        slug: str,
        target_time: datetime,
        *,
        resume: bool = False,
        speed: float = 60.0,
    ) -> ScenarioRun:
        """Replace the current run's state with the deterministic state at
        `target_time`. If `resume` is True, start the live clock from there.

        No SSE events are pushed for the historical replay, and no Telegram
        messages are sent — seek is a UI affordance, not a re-broadcast.
        """
        await self.stop(slug)

        ctx = _load_ctx(slug)
        if ctx is None:
            raise ValueError(f"scenario not found: {slug}")

        # Clamp to scenario bounds.
        target = max(ctx.scenario_start, min(ctx.scenario_end, target_time))

        run = self._new_run(slug, speed if resume else 60.0)
        run.scenario_time = ctx.scenario_start

        # Walk synchronously to target_time. We loop strictly less-than-or-equal
        # so the tick at target_time is fully processed.
        while run.scenario_time <= target:
            await _advance_one_tick(
                run, ctx,
                queue_events=False,
                dispatch=False,
                send_message=None,
            )

        # _advance_one_tick has incremented scenario_time past target. Rewind
        # one step so the run sits exactly at target (next tick will be target + step).
        run.scenario_time -= TICK_STEP
        # Reset stopped flag (paranoia; a freshly-built run is not stopped).
        run.stopped = False

        self.runs[slug] = run

        # Push a `state` event so any subsequently-opened SSE stream sees the
        # snapshot (the /events route already replays state on connect).
        await run.queue.put(_serialize_event("state", {
            "scenario_time": run.scenario_time.isoformat() if run.scenario_time else None,
            "track_so_far": run.track_so_far,
            "impact_zones": list(run.impact_zones.values()),
            "alerts": run.alerts,
            "signals": run.signals,
            "running": resume,
            "speed": run.speed,
        }))

        if resume:
            run.task = asyncio.create_task(self._run_loop(run), name=f"scenario:{slug}")

        return run

    async def _run_loop(self, run: ScenarioRun) -> None:
        try:
            await self._drive(run)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("scenario loop crashed: %s", exc)
            await run.queue.put({"event": "done", "data": json.dumps({"reason": f"error:{exc}"})})

    async def _drive(self, run: ScenarioRun) -> None:
        ctx = _load_ctx(run.scenario_slug)
        if ctx is None:
            await run.queue.put({"event": "done", "data": json.dumps({"reason": "not_found"})})
            return

        # Honor pre-populated scenario_time (e.g. resume after seek).
        if run.scenario_time is None:
            run.scenario_time = ctx.scenario_start
        else:
            # Resume on the next tick boundary, not the one we already processed in seek.
            run.scenario_time = run.scenario_time + TICK_STEP

        sleep_seconds = TICK_STEP.total_seconds() / run.speed

        while not run.stopped and run.scenario_time <= ctx.scenario_end:
            await _advance_one_tick(
                run, ctx,
                queue_events=True,
                dispatch=True,
                send_message=self._send_message,
            )
            try:
                await asyncio.sleep(sleep_seconds)
            except asyncio.CancelledError:
                raise

        await run.queue.put(_serialize_event("done", {
            "reason": "completed",
            "alerts_issued": len(run.alerts),
            "signals_surfaced": len(run.signals),
        }))


_runner = ScenarioRunner()


def get_runner() -> ScenarioRunner:
    return _runner
