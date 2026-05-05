from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Severity(str, enum.Enum):
    advisory = "advisory"
    warning = "warning"
    urgent = "urgent"


class Classification(str, enum.Enum):
    distress = "distress"
    observation = "observation"
    noise = "noise"


class HazardType(str, enum.Enum):
    typhoon = "typhoon"
    flood = "flood"
    earthquake = "earthquake"
    volcano = "volcano"


class Country(Base):
    __tablename__ = "countries"

    code: Mapped[str] = mapped_column(String(2), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    default_language: Mapped[str] = mapped_column(String(8), nullable=False)
    dominant_platform: Mapped[str] = mapped_column(String(32), nullable=False, default="telegram")

    municipalities: Mapped[list["Municipality"]] = relationship(back_populates="country")


class Municipality(Base):
    __tablename__ = "municipalities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    country_code: Mapped[str] = mapped_column(ForeignKey("countries.code"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    population: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    geom_geojson: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    country: Mapped[Country] = relationship(back_populates="municipalities")


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    hazard_type: Mapped[HazardType] = mapped_column(Enum(HazardType), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    track_points: Mapped[list["TrackPoint"]] = relationship(
        back_populates="scenario", order_by="TrackPoint.timestamp"
    )
    alerts: Mapped[list["Alert"]] = relationship(back_populates="scenario")
    signals: Mapped[list["Signal"]] = relationship(back_populates="scenario")


class TrackPoint(Base):
    __tablename__ = "track_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    max_wind_kt: Mapped[float] = mapped_column(Float, nullable=False)
    pressure_mb: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    scenario: Mapped[Scenario] = relationship(back_populates="track_points")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_chat_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    country_code: Mapped[str] = mapped_column(ForeignKey("countries.code"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id"), nullable=False, index=True)
    country_code: Mapped[str] = mapped_column(ForeignKey("countries.code"), nullable=False, index=True)
    municipality_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("municipalities.id"), nullable=True, index=True
    )
    severity: Mapped[Severity] = mapped_column(Enum(Severity), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False)

    scenario: Mapped[Scenario] = relationship(back_populates="alerts")
    municipality: Mapped[Optional[Municipality]] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "scenario_id", "country_code", "municipality_id", "severity", "language",
            name="uq_alert_dedup",
        ),
    )


class AlertDelivery(Base):
    __tablename__ = "alert_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"), nullable=False, index=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id"), nullable=False, index=True
    )
    delivered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="sent")


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="social")
    text: Mapped[str] = mapped_column(Text, nullable=False)
    classification: Mapped[Classification] = mapped_column(Enum(Classification), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    scenario: Mapped[Scenario] = relationship(back_populates="signals")
