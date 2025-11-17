"""Schemas for integration and onboarding endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CompanyProfile(BaseModel):
    """Basic company profile collected from the Telegram Web App."""

    user_id: str = Field(description="Telegram user identifier")
    company_name: str = Field(description="Company name provided by the user")
    industry: Optional[str] = Field(default=None, description="Industry or segment")
    employees: Optional[int] = Field(default=None, description="Employee count if provided")
    annual_revenue: Optional[str] = Field(default=None, description="Revenue description or range")
    key_systems: Optional[str] = Field(default=None, description="Key systems or tools used")
    goals: Optional[str] = Field(default=None, description="Main goals user expects from the assistant")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CompanyProfileResponse(BaseModel):
    """Response payload after profile persistence."""

    status: str = Field(default="ok")
    profile: CompanyProfile


class IntegrationConfirmation(BaseModel):
    """Payload confirming Alfa Business enablement."""

    user_id: str = Field(description="Telegram user identifier")
    provider: str = Field(default="alpha_business", description="Integration provider name")
    connected_at: datetime = Field(default_factory=datetime.utcnow)


class IntegrationStatus(BaseModel):
    """Stored status of external integration."""

    status: str = Field(default="disconnected")
    provider: str = Field(default="alpha_business")
    connected_at: Optional[datetime] = None


class IntegrationConfirmationResponse(BaseModel):
    """Response payload for integration confirmation."""

    status: str = Field(default="ok")
    integration: IntegrationStatus


class ProfileIndexStatus(BaseModel):
    """Status of profile indexing workflow."""

    status: str
    queued_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    reason: Optional[str] = None


class OnboardingStateResponse(BaseModel):
    """Aggregated onboarding state for Web App."""

    user_id: str
    profile: Optional[CompanyProfile] = None
    profile_status: Optional[ProfileIndexStatus] = None
    integration: Optional[IntegrationStatus] = None
