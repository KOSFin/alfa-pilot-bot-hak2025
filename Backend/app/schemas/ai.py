from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field

from .base import BaseSchema


class PlannerResponse(BaseSchema):

    intent: Literal["advisor", "calculator"]
    confidence: float = Field(default=0.5)
    next_prompt: str
    brief: Optional[str] = None
    tool_plan: list[str] = Field(default_factory=list)
    calculator_payload: dict | None = None


class CalculatorPrompt(BaseSchema):

    instructions: str
    parameters: dict = Field(default_factory=dict)
    confirmation_text: str


class AdvisorPrompt(BaseSchema):

    instructions: str
    context: str
