from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import Scenario, Signal
from ..schemas import SignalOut

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("", response_model=list[SignalOut])
def list_signals(
    scenario: str = Query(...),
    session: Session = Depends(get_session),
) -> list[SignalOut]:
    sc = session.execute(select(Scenario).where(Scenario.slug == scenario)).scalar_one_or_none()
    if sc is None:
        raise HTTPException(404, detail={"error": {"code": "not_found", "message": "scenario not found"}})
    rows = session.execute(
        select(Signal).where(Signal.scenario_id == sc.id).order_by(Signal.timestamp)
    ).scalars().all()
    return [SignalOut.model_validate(s) for s in rows]
