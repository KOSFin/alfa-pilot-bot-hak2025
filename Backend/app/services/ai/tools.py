"""Implements runtime tools that the AI can use."""
from __future__ import annotations

import contextlib
import io
import textwrap
import time
from typing import Any, Dict

from ...config import get_settings
from ...schemas.chat import ToolExecutionRequest, ToolExecutionResult


class RestrictedPythonExecutor:
    """Executes Python code snippets in a controlled namespace."""

    SAFE_BUILTINS: Dict[str, Any] = {
        "abs": abs,
        "min": min,
        "max": max,
        "sum": sum,
        "len": len,
        "range": range,
        "enumerate": enumerate,
        "round": round,
        "sorted": sorted,
    }

    def __init__(self) -> None:
        settings = get_settings()
        self._timeout = settings.calculator_timeout_sec

    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        locals_namespace = dict(request.variables)
        stdout = io.StringIO()
        code = textwrap.dedent(request.code)
        start = time.perf_counter()
        try:
            with contextlib.redirect_stdout(stdout):
                exec(  # noqa: S102 - controlled namespace
                    code,
                    {"__builtins__": self.SAFE_BUILTINS},
                    locals_namespace,
                )
            duration = int((time.perf_counter() - start) * 1000)
            output_text = stdout.getvalue().strip()
            if "result" in locals_namespace:
                output_text += f"\nresult = {locals_namespace['result']}"
            return ToolExecutionResult(
                name=request.name,
                output=output_text or "<no output>",
                success=True,
                error=None,
                duration_ms=duration,
            )
        except Exception as exc:  # pylint: disable=broad-except
            duration = int((time.perf_counter() - start) * 1000)
            return ToolExecutionResult(
                name=request.name,
                output=stdout.getvalue().strip(),
                success=False,
                error=str(exc),
                duration_ms=duration,
            )


class ToolRegistry:
    """Maps tool names to execution implementations."""

    def __init__(self) -> None:
        self._python_executor = RestrictedPythonExecutor()

    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        if request.name == "python_code_executor":
            return self._python_executor.execute(request)
        return ToolExecutionResult(name=request.name, output="", success=False, error="Unknown tool", duration_ms=0)
