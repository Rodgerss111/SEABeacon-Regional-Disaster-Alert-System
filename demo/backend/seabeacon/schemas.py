from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .models import Classification, HazardType, Severity


class CountryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    default_language: str
    dominant_platform: str


class MunicipalityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    country_code: str
    name: str
    lat: float
    lon: float
    population: int


class TrackPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    lat: float
    lon: float
    max_wind_kt: float
    pressure_mb: float
    category: int


class ScenarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    hazard_type: HazardType
    start_time: datetime
    end_time: datetime
    description: str


class ScenarioDetail(ScenarioOut):
    track_points: list[TrackPointOut] = Field(default_factory=list)


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scenario_id: int
    country_code: str
    municipality_id: Optional[int]
    severity: Severity
    issued_at: datetime
    title: str
    body: str
    language: str


class SignalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    lat: float
    lon: float
    language: str
    source_type: str
    text: str
    classification: Classification
    confidence: float


class SubscriptionIn(BaseModel):
    telegram_chat_id: int
    language: str = "en"
    country_code: str


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_chat_id: int
    language: str
    country_code: str
    active: bool
    created_at: datetime


class RunRequest(BaseModel):
    speed: float = 60.0  # scenario seconds per real second


class RunResponse(BaseModel):
    run_id: str
    scenario_slug: str
    speed: float
    started_at: datetime


class SeekRequest(BaseModel):
    scenario_time: datetime
    resume: bool = False
    speed: float = 60.0


class ImpactZoneOut(BaseModel):
    municipality_id: int
    municipality_name: str
    country_code: str
    lat: float
    lon: float
    severity: Severity
    eta_hours: float
    confidence: float


class ScenarioState(BaseModel):
    scenario_slug: str
    running: bool
    speed: float
    scenario_time: Optional[datetime]
    current_point: Optional[TrackPointOut]
    track_so_far: list[TrackPointOut] = Field(default_factory=list)
    impact_zones: list[ImpactZoneOut] = Field(default_factory=list)
    alerts: list[AlertOut] = Field(default_factory=list)
    signals: list[SignalOut] = Field(default_factory=list)


class SeekResponse(BaseModel):
    scenario_slug: str
    scenario_time: Optional[datetime]
    running: bool
    speed: float
    track_so_far: list[dict] = Field(default_factory=list)
    impact_zones: list[ImpactZoneOut] = Field(default_factory=list)
    alerts: list[dict] = Field(default_factory=list)
    signals: list[SignalOut] = Field(default_factory=list)
    current_point: Optional[TrackPointOut] = None
