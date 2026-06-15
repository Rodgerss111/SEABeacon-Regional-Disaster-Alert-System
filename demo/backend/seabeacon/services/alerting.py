"""Alert creation + dispatch.

Persists Alerts (one per (scenario, country, muni, severity, language) tuple),
records AlertDeliveries to subscribers in the matching country and language,
and pushes the messages via the Telegram dispatcher.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import Alert, AlertDelivery, HazardType, Subscription
from .localization import SUPPORTED_LANGUAGES, render_alert
from .propagation import ImpactPrediction


def _existing_alert(session: Session, *, scenario_id: int, country_code: str,
                    municipality_id: int, severity: str, language: str) -> Optional[Alert]:
    stmt = select(Alert).where(
        Alert.scenario_id == scenario_id,
        Alert.country_code == country_code,
        Alert.municipality_id == municipality_id,
        Alert.severity == severity,
        Alert.language == language,
    )
    return session.execute(stmt).scalar_one_or_none()


def create_alerts_for_prediction(
    session: Session,
    *,
    scenario_id: int,
    hazard_type: HazardType,
    storm_name: str,
    issued_at: datetime,
    prediction: ImpactPrediction,
) -> tuple[list[Alert], list[Alert]]:
    """Ensure one Alert row per supported language for this prediction.

    Returns (all_alerts, new_alerts) so callers can decide what to dispatch.
    Existing alerts are returned alongside any newly-created ones — useful for
    seek-style replays where the run state must reflect every alert that
    would have been issued, regardless of whether it was persisted before.
    """
    all_alerts: list[Alert] = []
    new_alerts: list[Alert] = []

    for language in SUPPORTED_LANGUAGES:
        existing = _existing_alert(
            session,
            scenario_id=scenario_id,
            country_code=prediction.country_code,
            municipality_id=prediction.municipality_id,
            severity=prediction.severity.value,
            language=language,
        )
        if existing is not None:
            all_alerts.append(existing)
            continue

        title, body = render_alert(
            hazard_type=hazard_type,
            severity=prediction.severity,
            language=language,
            municipality=prediction.municipality_name,
            storm_name=storm_name,
            category=4,  # filled by caller; safe default for demo
            eta_hours=prediction.eta_hours,
        )
        alert = Alert(
            scenario_id=scenario_id,
            country_code=prediction.country_code,
            municipality_id=prediction.municipality_id,
            severity=prediction.severity,
            issued_at=issued_at,
            title=title,
            body=body,
            language=language,
        )
        session.add(alert)
        try:
            session.flush()
        except IntegrityError:
            session.rollback()
            # Re-fetch in case another tick raced us.
            re = _existing_alert(
                session,
                scenario_id=scenario_id,
                country_code=prediction.country_code,
                municipality_id=prediction.municipality_id,
                severity=prediction.severity.value,
                language=language,
            )
            if re is not None:
                all_alerts.append(re)
            continue
        all_alerts.append(alert)
        new_alerts.append(alert)
    return all_alerts, new_alerts


async def dispatch_alert_to_subscribers(
    session: Session,
    alert: Alert,
    *,
    send_message,  # async callable: (chat_id: int, text: str) -> bool
) -> int:
    """Send `alert` to every active subscriber in the country + language match.

    Returns the number of successful sends. Records an AlertDelivery row per
    subscriber (sent or failed).
    """
    subs = session.execute(
        select(Subscription).where(
            Subscription.country_code == alert.country_code,
            Subscription.language == alert.language,
            Subscription.active.is_(True),
        )
    ).scalars().all()

    sent = 0
    for sub in subs:
        text = f"*{alert.title}*\n\n{alert.body}"
        try:
            ok = await send_message(sub.telegram_chat_id, text)
            status = "sent" if ok else "failed:send_returned_false"
            if ok:
                sent += 1
        except Exception as exc:  # noqa: BLE001
            status = f"failed:{type(exc).__name__}"

        session.add(AlertDelivery(alert_id=alert.id, subscription_id=sub.id, status=status))
        await asyncio.sleep(0.05)  # ~20 msg/s, well under Telegram's 30/s limit
    session.flush()
    return sent
