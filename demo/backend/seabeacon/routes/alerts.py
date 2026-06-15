from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import Alert, Scenario
from ..schemas import AlertOut

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def list_alerts(
    scenario: str = Query(...),
    session: Session = Depends(get_session),
) -> list[AlertOut]:
    sc = session.execute(select(Scenario).where(Scenario.slug == scenario)).scalar_one_or_none()
    if sc is None:
        raise HTTPException(404, detail={"error": {"code": "not_found", "message": "scenario not found"}})

    rows = session.execute(
        select(Alert).where(Alert.scenario_id == sc.id).order_by(Alert.issued_at.desc())
    ).scalars().all()
    return [AlertOut.model_validate(a) for a in rows]
