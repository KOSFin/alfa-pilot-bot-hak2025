"""Schemas for chat and dialog flows."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import Field

from .base import BaseSchema


class MessageRole:
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ChatMessage(BaseSchema):
    """Single chat exchange item."""

    role: Literal["user", "assistant", "system", "tool"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict | None = None


class ChatTurn(BaseSchema):
    """Conversation turn combining request and response."""

    user_id: str
    messages: list[ChatMessage]
    thread_id: str | None = None
    session_id: str | None = None


class ChatRequest(BaseSchema):
    """Incoming chat message payload."""

    user_id: str
    content: str
    metadata: dict | None = None


class ChatResponse(BaseSchema):
    """Response returned to frontend."""

    reply: ChatMessage
    decision: OrchestrationDecision
    knowledge_hits: list[dict]
    tool_results: list[ToolExecutionResult]


class CalculatorPlan(BaseSchema):
    """Structured plan produced before executing calculator."""

    plan_id: str
    description: str
    variables: dict
    formulas: list[str]
    suggested_tool: str
    followups: list[str]
    original_message: ChatMessage


class CalculatorConfirmationRequest(BaseSchema):
    """User confirmation payload for executing calculations."""

    plan_id: str
    user_id: str
    confirmed: bool


class CalculatorExecutionRequest(BaseSchema):
    """Request body for executing calculator once confirmed."""

    plan_id: str
    user_id: str


class OrchestrationDecision(BaseSchema):
    """Result of AI planner deciding what to do."""

    mode: Literal["advisor", "calculator"]
    summary: Optional[str] = None
    calculator_instructions: Optional[str] = None
    tool_calls: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class ToolExecutionRequest(BaseSchema):
    """Request for executing a calculator tool."""

    name: str
    code: str
    variables: dict = Field(default_factory=dict)
    rationale: str | None = None


class ToolExecutionResult(BaseSchema):
    """Outcome of tool execution."""

    name: str
    output: str
    success: bool = True
    error: str | None = None
    duration_ms: int | None = None
