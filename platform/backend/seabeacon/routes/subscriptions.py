from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import Country, Subscription
from ..schemas import SubscriptionIn, SubscriptionOut

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post("", response_model=SubscriptionOut)
def create_subscription(body: SubscriptionIn, session: Session = Depends(get_session)) -> SubscriptionOut:
    if not session.get(Country, body.country_code):
        raise HTTPException(400, detail={"error": {"code": "bad_country", "message": "unknown country code"}})

    sub = session.execute(
        select(Subscription).where(Subscription.telegram_chat_id == body.telegram_chat_id)
    ).scalar_one_or_none()
    if sub:
        sub.language = body.language
        sub.country_code = body.country_code
        sub.active = True
    else:
        sub = Subscription(
            telegram_chat_id=body.telegram_chat_id,
            language=body.language,
            country_code=body.country_code,
            active=True,
        )
        session.add(sub)
    session.commit()
    session.refresh(sub)
    return SubscriptionOut.model_validate(sub)


@router.get("/{telegram_chat_id}", response_model=SubscriptionOut)
def get_subscription(telegram_chat_id: int, session: Session = Depends(get_session)) -> SubscriptionOut:
    sub = session.execute(
        select(Subscription).where(Subscription.telegram_chat_id == telegram_chat_id)
    ).scalar_one_or_none()
    if sub is None:
        raise HTTPException(404, detail={"error": {"code": "not_found", "message": "subscription not found"}})
    return SubscriptionOut.model_validate(sub)


@router.delete("/{telegram_chat_id}")
def delete_subscription(telegram_chat_id: int, session: Session = Depends(get_session)) -> dict:
    sub = session.execute(
        select(Subscription).where(Subscription.telegram_chat_id == telegram_chat_id)
    ).scalar_one_or_none()
    if sub is None:
        return {"deleted": False}
    sub.active = False
    session.commit()
    return {"deleted": True}
