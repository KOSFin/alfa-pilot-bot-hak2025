from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

from ..schemas.chat import (
    CalculatorExecutionRequest,
    CalculatorPlan,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    MessageRole,
    ToolExecutionResult,
)
from ..services.ai.orchestrator import AIOrchestrator
from ..services.calculators.engine import CalculatorEngine
from ..services.conversation.manager import ConversationManager
from ..services.storage.knowledge_base import KnowledgeBase
from ..services.storage.redis_store import RedisStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


def get_orchestrator(request: Request) -> AIOrchestrator:
    return request.app.state.orchestrator


def get_conversation(request: Request) -> ConversationManager:
    return request.app.state.conversation_manager


def get_knowledge_base(request: Request) -> KnowledgeBase:
    return request.app.state.knowledge_base


def get_calculator(request: Request) -> CalculatorEngine:
    return request.app.state.calculator_engine


def get_store() -> RedisStore:
    return RedisStore()


async def _get_company_profile_info(user_id: str, store: RedisStore) -> str | None:
    """Get company profile information for the user to enhance context."""
    try:
        profile_data = await store.get_json(f"company-profile:{user_id}")
        if profile_data and profile_data.get("company_name"):
            company_info_parts = [f"Название компании: {profile_data.get('company_name')}"]
            if profile_data.get("industry"):
                company_info_parts.append(f"Индустрия: {profile_data.get('industry')}")
            if profile_data.get("employees"):
                company_info_parts.append(f"Количество сотрудников: {profile_data.get('employees')}")
            if profile_data.get("annual_revenue"):
                company_info_parts.append(f"Выручка: {profile_data.get('annual_revenue')}")
            if profile_data.get("goals"):
                company_info_parts.append(f"Цели: {profile_data.get('goals')}")

            return "\n".join(company_info_parts)
    except Exception as e:
        logger.warning(f"Could not retrieve company profile for user {user_id}: {e}")
    return None


@router.post("/messages", response_model=ChatResponse)
async def post_message(
    payload: ChatRequest,
    orchestrator: AIOrchestrator = Depends(get_orchestrator),
    conversation: ConversationManager = Depends(get_conversation),
    knowledge_base: KnowledgeBase = Depends(get_knowledge_base),
    store: RedisStore = Depends(get_store),
) -> ChatResponse:
    user_message = ChatMessage(role=MessageRole.USER, content=payload.content, metadata=payload.metadata)
    await conversation.append_messages(payload.user_id, [user_message])
    history = await conversation.get_recent_messages(payload.user_id)

    company_info = await _get_company_profile_info(payload.user_id, store)

    knowledge = await knowledge_base.search(payload.content, user_id=payload.user_id)

    if company_info:
        company_related_keywords = ["компания", "называется", "название", "организация", "фирма", "наша", "моей", "моя", "мы"]
        is_company_query = any(keyword in payload.content.lower() for keyword in company_related_keywords)

        if is_company_query:
            from ..schemas.knowledge import KnowledgeSearchHit
            company_hit = KnowledgeSearchHit(
                id="company_profile",
                score=10.0,
                text=company_info,
                metadata={"source": "company_profile", "type": "company_info"}
            )
            knowledge.hits.insert(0, company_hit)

    decision = await orchestrator.decide(user_message, history, knowledge)

    if decision.mode == "advisor":
        reply_text = await orchestrator.draft_advisor_reply(user_message, history, knowledge)
        reply = ChatMessage(role=MessageRole.ASSISTANT, content=reply_text)
        await conversation.append_messages(payload.user_id, [reply])
        await knowledge_base.index_dialog(
            f"advisor:{payload.user_id}:{uuid.uuid4()}",
            f"User: {payload.content}\nAssistant: {reply_text}",
            {"user_id": payload.user_id, "mode": "advisor"},
        )
        return ChatResponse(
            reply=reply,
            decision=decision,
            knowledge_hits=[hit.model_dump() if hasattr(hit, "model_dump") else hit for hit in knowledge.hits],
            tool_results=[],
        )

    plan_raw = await orchestrator.draft_calculator_plan(user_message, knowledge, decision.calculator_instructions)
    plan_id = str(uuid.uuid4())
    plan = CalculatorPlan(
        plan_id=plan_id,
        description=plan_raw.get("description", ""),
        variables=plan_raw.get("variables", {}),
        formulas=plan_raw.get("formulas", []),
        suggested_tool=plan_raw.get("suggested_tool", "python_code_executor"),
        followups=plan_raw.get("followups", []),
        original_message=user_message,
    )
    await store.set_json(
        f"plan:{plan_id}",
        {
            "plan": plan.model_dump(mode="json"),
            "user_id": payload.user_id,
            "decision": decision.model_dump(mode="json"),
            "knowledge": [hit.model_dump() if hasattr(hit, "model_dump") else hit for hit in knowledge.hits],
        },
        expire=60 * 30,
    )
    reply = ChatMessage(
        role=MessageRole.ASSISTANT,
        content=(
            "Я подготовил план расчёта. Подтвердите, пожалуйста, выполнение.\n"
            f"Описание: {plan.description}\n"
            f"Переменные: {plan.variables}\n"
            f"Формулы: {plan.formulas}"
        ),
        metadata={"plan_id": plan_id, "followups": plan.followups},
    )
    await conversation.append_messages(payload.user_id, [reply])
    return ChatResponse(
        reply=reply,
        decision=decision,
        knowledge_hits=[hit.model_dump() if hasattr(hit, "model_dump") else hit for hit in knowledge.hits],
        tool_results=[],
    )


@router.post("/execute", response_model=ChatResponse)
async def execute_plan(
    payload: CalculatorExecutionRequest,
    orchestrator: AIOrchestrator = Depends(get_orchestrator),
    conversation: ConversationManager = Depends(get_conversation),
    knowledge_base: KnowledgeBase = Depends(get_knowledge_base),
    calculator: CalculatorEngine = Depends(get_calculator),
    store: RedisStore = Depends(get_store),
) -> ChatResponse:
    key = f"plan:{payload.plan_id}"
    data = await store.get_json(key)
    if not data:
        raise HTTPException(status_code=404, detail="Plan expired or not found")
    if data.get("user_id") != payload.user_id:
        raise HTTPException(status_code=403, detail="Plan ownership mismatch")

    plan_payload = data["plan"]
    original_message = ChatMessage(**plan_payload["original_message"])
    decision = data["decision"]
    knowledge_hits = data.get("knowledge", [])

    variables = dict(plan_payload.get("variables", {}))
    code = variables.pop("code", "")
    tool_request_payload = {
        "name": plan_payload.get("suggested_tool", "python_code_executor"),
        "code": code,
        "variables": variables,
        "rationale": plan_payload.get("description"),
    }
    result: ToolExecutionResult = calculator.run(tool_request_payload)
    tool_results = [result]

    reply_text, tools_used = await orchestrator.draft_calculator_reply(plan_payload, [result.model_dump()])

    reply = ChatMessage(
        role=MessageRole.ASSISTANT,
        content=reply_text,
        metadata={"tools_used": tools_used}
    )

    await conversation.append_messages(payload.user_id, [reply])
    await knowledge_base.index_dialog(
        f"calc:{payload.user_id}:{uuid.uuid4()}",
        f"User: {original_message.content}\nAssistant: {reply_text}",
        {"user_id": payload.user_id, "mode": "calculator"},
    )

    await store.delete(key)

    return ChatResponse(
        reply=reply,
        decision=decision,
        knowledge_hits=knowledge_hits,
        tool_results=tool_results,
    )


@router.delete("/context/{user_id}")
async def reset_context(
    user_id: str,
    conversation: ConversationManager = Depends(get_conversation),
    store: RedisStore = Depends(get_store),
) -> dict[str, str]:
    """Reset conversation context for the specified user."""
    try:
        key = f"dialog:{user_id}"
        await store.delete(key)

        return {"status": "success", "message": f"Context for user {user_id} has been reset"}
    except Exception as e:
        logger.error(f"Error resetting context for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset context")
