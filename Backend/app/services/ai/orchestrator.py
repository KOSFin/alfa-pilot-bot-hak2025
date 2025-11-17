"""High-level orchestration logic for deciding responses."""
from __future__ import annotations

import json
import logging
from textwrap import dedent
from typing import Any

from ...schemas.chat import ChatMessage, OrchestrationDecision
from ...schemas.knowledge import KnowledgeSearchResponse
from .gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class AIOrchestrator:
    """Decides whether to respond as advisor or invoke calculator branch."""

    def __init__(self) -> None:
        self._gemini = GeminiClient()

    async def decide(self, message: ChatMessage, history: list[ChatMessage], knowledge: KnowledgeSearchResponse) -> OrchestrationDecision:
        prompt = self._build_prompt(message, history, knowledge)
        schema = {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["advisor", "calculator"],
                },
                "summary": {"type": "string"},
                "calculator_instructions": {"type": "string"},
                "tool_calls": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "metadata": {
                    "type": "object",
                    "properties": {
                        "notes": {"type": "string"},
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
            "required": ["mode"],
            "additionalProperties": False,
        }
        logger.debug("Sending orchestration prompt to Gemini")
        response = await self._gemini.generate_structured(prompt, schema=schema)
        logger.debug("Planner raw response: %s", response)
        return OrchestrationDecision(**response)

    def _build_prompt(self, message: ChatMessage, history: list[ChatMessage], knowledge: KnowledgeSearchResponse) -> str:
        history_text = "\n".join(
            f"{item.role}: {item.content}" for item in history[-8:]
        )
        kb_snippets = "\n".join(
            f"Score {hit.score:.2f} | {hit.text[:512]}" for hit in knowledge.hits
        )
        prompt = dedent(
            f"""
            You are Alfa Pilot, an AI that assists SMEs with finance tasks and planning.
            Analyze the user message and decide whether it requests advisory response or a calculator-based computation.

            Conversation history:
            {history_text}

            Knowledge base context:
            {kb_snippets or 'No relevant documents.'}

            Current user message:
            {message.content}

            Respond with JSON describing the mode selection. Select "calculator" whenever the user expects numbers, forecasting, budgeting, cost breakdowns or explicit calculations; otherwise choose "advisor". When choosing calculator, outline calculator instructions to confirm with the user and name required tool calls if any (e.g., python_code_executor).
            """
        ).strip()
        return prompt

    async def draft_advisor_reply(self, message: ChatMessage, history: list[ChatMessage], knowledge: KnowledgeSearchResponse) -> str:
        prompt = dedent(
            f"""
            You are Alfa Pilot AI advisor. Use the knowledge base extracts and conversation history to craft a concise, actionable reply.

            Conversation history (last turns):
            {'\n'.join(f'{item.role}: {item.content}' for item in history[-6:])}

            Knowledge base context:
            {'\n'.join(f'- {hit.text[:512]}' for hit in knowledge.hits) or 'No extra context.'}

            User message:
            {message.content}

            Provide a professional, helpful answer in Russian. Include bullet points where it improves clarity.
            """
        ).strip()
        response = await self._gemini.generate_content(prompt)
        return response

    async def draft_calculator_plan(self, message: ChatMessage, knowledge: KnowledgeSearchResponse, instructions: str | None) -> dict[str, Any]:
        prompt = dedent(
            f"""
            You are Alfa Pilot AI planner preparing structured parameters for a financial calculation.
            User request: {message.content}
            Supplemental knowledge:
            {'\n'.join(f'- {hit.text[:512]}' for hit in knowledge.hits) or 'None'}

            Describe the inputs, assumptions, and formulas needed to calculate the result. Output a JSON with keys:
            - description: textual explanation for the confirmation step
            - variables: object with numeric or textual parameters inferred
            - formulas: list of textual formula descriptions
            - suggested_tool: name of tool to execute (python_code_executor by default)
            - followups: array of optional questions to clarify uncertainties
            """
        ).strip()
        if instructions:
            prompt += f"\nAdditional calculator instructions from planner: {instructions}"
        schema = {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "variables": {"type": "object"},
                "formulas": {"type": "array", "items": {"type": "string"}},
                "suggested_tool": {"type": "string"},
                "followups": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["description", "variables"],
        }
        response = await self._gemini.generate_structured(prompt, schema=schema)
        return {
            "description": response.get("description", ""),
            "variables": response.get("variables", {}),
            "formulas": response.get("formulas", []),
            "suggested_tool": response.get("suggested_tool", "python_code_executor"),
            "followups": response.get("followups", []),
        }

    async def draft_calculator_reply(self, confirmation_payload: dict[str, Any], tool_results: list[dict[str, Any]]) -> str:
        prompt = dedent(
            f"""
            You are Alfa Pilot AI. Summarize the calculation for the user using the plan and tool execution results.

            Plan: {json.dumps(confirmation_payload, ensure_ascii=False)}
            Tool results: {json.dumps(tool_results, ensure_ascii=False)}

            Respond in Russian, highlight methodology, assumptions, and final values. Provide next-step recommendations if relevant.
            """
        ).strip()
        response = await self._gemini.generate_content(prompt)
        return response
