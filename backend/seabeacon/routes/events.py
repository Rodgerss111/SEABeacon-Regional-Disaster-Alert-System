from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from ..services.scenario_clock import get_runner

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/{scenario_slug}")
async def stream_events(scenario_slug: str):
    runner = get_runner()
    run = runner.runs.get(scenario_slug)
    if run is None:
        raise HTTPException(
            404,
            detail={"error": {"code": "no_active_run", "message": "Start the scenario first via POST /scenarios/{slug}/run"}},
        )

    async def event_gen():
        # Replay current state so a late-joining client gets existing track/alerts.
        initial = {
            "scenario_time": run.scenario_time.isoformat() if run.scenario_time else None,
            "track_so_far": run.track_so_far,
            "impact_zones": list(run.impact_zones.values()),
            "alerts": run.alerts,
            "signals": run.signals,
            "running": not run.stopped,
            "speed": run.speed,
        }
        yield {"event": "state", "data": json.dumps(initial, default=str)}

        while True:
            try:
                msg = await asyncio.wait_for(run.queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                yield {"event": "ping", "data": "{}"}
                if run.stopped:
                    break
                continue
            yield msg
            if msg.get("event") == "done":
                break

    return EventSourceResponse(event_gen())
