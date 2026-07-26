from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import Scenario
from ..schemas import (
    ImpactZoneOut,
    RunRequest,
    RunResponse,
    ScenarioDetail,
    ScenarioOut,
    ScenarioState,
    SeekRequest,
    SeekResponse,
    TrackPointOut,
)
from ..services.scenario_clock import get_runner

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


def _get_scenario(session: Session, slug: str) -> Scenario:
    sc = session.execute(select(Scenario).where(Scenario.slug == slug)).scalar_one_or_none()
    if sc is None:
        raise HTTPException(404, detail={"error": {"code": "not_found", "message": f"Scenario '{slug}' not found"}})
    return sc


@router.get("", response_model=list[ScenarioOut])
def list_scenarios(session: Session = Depends(get_session)) -> list[ScenarioOut]:
    rows = session.execute(select(Scenario).order_by(Scenario.id)).scalars().all()
    return [ScenarioOut.model_validate(r) for r in rows]


@router.get("/{slug}", response_model=ScenarioDetail)
def get_scenario(slug: str, session: Session = Depends(get_session)) -> ScenarioDetail:
    sc = _get_scenario(session, slug)
    return ScenarioDetail(
        id=sc.id,
        slug=sc.slug,
        name=sc.name,
        hazard_type=sc.hazard_type,
        start_time=sc.start_time,
        end_time=sc.end_time,
        description=sc.description,
        track_points=[TrackPointOut.model_validate(p) for p in sc.track_points],
    )


@router.post("/{slug}/run", response_model=RunResponse)
async def run_scenario(slug: str, body: RunRequest, session: Session = Depends(get_session)) -> RunResponse:
    sc = _get_scenario(session, slug)
    runner = get_runner()
    run = await runner.start(sc.slug, body.speed)
    return RunResponse(
        run_id=run.run_id,
        scenario_slug=sc.slug,
        speed=run.speed,
        started_at=run.started_at,
    )


@router.post("/{slug}/stop")
async def stop_scenario(slug: str, session: Session = Depends(get_session)) -> dict:
    _get_scenario(session, slug)
    runner = get_runner()
    await runner.stop(slug)
    return {"stopped": slug}


@router.post("/{slug}/seek", response_model=SeekResponse)
async def seek_scenario(
    slug: str, body: SeekRequest, session: Session = Depends(get_session)
) -> SeekResponse:
    sc = _get_scenario(session, slug)
    runner = get_runner()
    target = body.scenario_time
    if target.tzinfo is not None:
        target = target.replace(tzinfo=None)
    run = await runner.seek(sc.slug, target, resume=body.resume, speed=body.speed)

    current_pt = None
    if run.current_point is not None:
        current_pt = TrackPointOut(
            id=0,
            timestamp=run.current_point.timestamp,
            lat=run.current_point.lat,
            lon=run.current_point.lon,
            max_wind_kt=run.current_point.max_wind_kt,
            pressure_mb=run.current_point.pressure_mb,
            category=run.current_point.category,
        )

    return SeekResponse(
        scenario_slug=sc.slug,
        scenario_time=run.scenario_time,
        running=body.resume,
        speed=run.speed,
        track_so_far=run.track_so_far,
        impact_zones=[ImpactZoneOut(**z) for z in run.impact_zones.values()],
        alerts=run.alerts,
        signals=run.signals,  # already serialized dicts
        current_point=current_pt,
    )


@router.get("/{slug}/state", response_model=ScenarioState)
def scenario_state(slug: str, session: Session = Depends(get_session)) -> ScenarioState:
    _get_scenario(session, slug)
    runner = get_runner()
    run = runner.runs.get(slug)
    if run is None:
        return ScenarioState(scenario_slug=slug, running=False, speed=0.0, scenario_time=None, current_point=None)

    current_pt = None
    if run.current_point is not None:
        current_pt = TrackPointOut(
            id=0,
            timestamp=run.current_point.timestamp,
            lat=run.current_point.lat,
            lon=run.current_point.lon,
            max_wind_kt=run.current_point.max_wind_kt,
            pressure_mb=run.current_point.pressure_mb,
            category=run.current_point.category,
        )

    track_so_far = [
        TrackPointOut(id=i, **p) for i, p in enumerate(run.track_so_far)
    ]
    impact_zones = [ImpactZoneOut(**z) for z in run.impact_zones.values()]

    return ScenarioState(
        scenario_slug=slug,
        running=not run.stopped,
        speed=run.speed,
        scenario_time=run.scenario_time,
        current_point=current_pt,
        track_so_far=track_so_far,
        impact_zones=impact_zones,
        alerts=[],  # full list available at /alerts; keep state lean
        signals=[],
    )


