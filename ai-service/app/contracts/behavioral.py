"""
Behavioral Intelligence (AI-07) HTTP contracts.

Wire format uses camelCase to stay compatible with the Node backend (Prisma models /
Flutter payloads), while Python code keeps snake_case via Pydantic v2 aliases. All
models tolerate extra fields (forward-compat with future backend changes) and accept
both snake_case and camelCase inputs (``populate_by_name=True``).

Scope: pure data contracts. No business logic, no DB access, no logging.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# === Request contracts ===


class UsageEventPayload(BaseModel):
    """One behavioral event as stored in Prisma ``UsageEvent`` and uploaded by the app."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    event_type: Literal["app_session", "unlock", "screen_on"] = Field(alias="eventType")
    app_package: Optional[str] = Field(default=None, alias="appPackage")
    started_at: datetime = Field(alias="startedAt")
    ended_at: Optional[datetime] = Field(default=None, alias="endedAt")
    duration_sec: Optional[int] = Field(default=None, alias="durationSec")


class ContentAnalysesSummary(BaseModel):
    """Aggregated counts produced by the existing content moderation pipeline."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    educational_count: int = Field(default=0, alias="educationalCount")
    risky_count: int = Field(default=0, alias="riskyCount")
    dangerous_count: int = Field(default=0, alias="dangerousCount")
    total: int = Field(default=0)


class MissionSummary(BaseModel):
    """Aggregated mission engagement for the analysis window."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    completed: int = Field(default=0)
    assigned: int = Field(default=0)
    success_rate: float = Field(default=0.0, alias="successRate")


class BehavioralAnalysisRequest(BaseModel):
    """Request body for the Phase-6 behavioral analysis endpoint."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    user_id: int = Field(alias="userId")
    age_years: int = Field(alias="ageYears")
    window_days: int = Field(default=7, alias="windowDays")
    events: list[UsageEventPayload]
    content_analyses_summary: Optional[ContentAnalysesSummary] = Field(
        default=None, alias="contentAnalysesSummary"
    )
    mission_summary: Optional[MissionSummary] = Field(
        default=None, alias="missionSummary"
    )


# === Response contracts ===


class SubScore(BaseModel):
    """One explainable sub-score contributing to a global score."""

    model_config = ConfigDict(extra="ignore")

    name: str
    value: float
    feature_values: dict = Field(alias="featureValues")
    explanation_fr: str = Field(alias="explanationFr")


class RecommendationItem(BaseModel):
    """Structured recommendation aligned with Prisma's Recommendation model (Phase 2)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    type: str
    severity: Literal["low", "medium", "high", "positive"]
    message_fr: str = Field(alias="messageFr")
    action_payload: dict = Field(default_factory=dict, alias="actionPayload")
    target_audience: Literal["parent", "child", "both"] = Field(
        default="parent", alias="targetAudience"
    )
    triggering_subscore: Optional[str] = Field(default=None, alias="triggeringSubscore")
    triggering_value: Optional[float] = Field(default=None, alias="triggeringValue")


class MissionSuggestion(BaseModel):
    """Structured child-facing mission generated from behavioral subscores."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    description_fr: str = Field(alias="descriptionFr")
    difficulty: Literal["easy", "medium", "hard"]
    points: int
    triggering_subscore: str = Field(alias="triggeringSubscore")
    triggering_value: float = Field(alias="triggeringValue")
    target_audience: Literal["child"] = Field(default="child", alias="targetAudience")


class BehavioralAnalysisResponse(BaseModel):
    """Response body with both global scores and their 5 sub-scores each."""

    model_config = ConfigDict(extra="ignore")

    addiction_score: float = Field(alias="addictionScore")
    addiction_subscores: list[SubScore] = Field(alias="addictionSubscores")
    wellbeing_score: float = Field(alias="wellbeingScore")
    wellbeing_subscores: list[SubScore] = Field(alias="wellbeingSubscores")
    window_days: int = Field(alias="windowDays")
    computed_at: datetime = Field(alias="computedAt")
    recommendations: list[RecommendationItem] = Field(
        default_factory=list, alias="recommendations"
    )
    missions: list[MissionSuggestion] = Field(default_factory=list, alias="missions")
