"""Calculator execution pipeline."""
from __future__ import annotations

from typing import Any

from ...schemas.chat import ToolExecutionRequest, ToolExecutionResult
from ..ai.tools import ToolRegistry


class CalculatorEngine:
    """Executes calculator tool calls and aggregates responses."""

    def __init__(self) -> None:
        self._registry = ToolRegistry()

    def run(self, request_payload: dict[str, Any]) -> ToolExecutionResult:
        request = ToolExecutionRequest(**request_payload)
        return self._registry.execute(request)
