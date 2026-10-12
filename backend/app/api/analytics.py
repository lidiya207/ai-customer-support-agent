"""Analytics and agent-run APIs."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_support_or_admin
from app.database.session import get_db
from app.models.user import User
from app.services import persistence

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/analytics/overview")
def analytics_overview(
    _: User = Depends(require_support_or_admin),
    db: Session = Depends(get_db),
) -> dict:
    return persistence.analytics_overview(db)


@router.get("/agent-runs")
def list_agent_runs(
    _: User = Depends(require_support_or_admin),
    db: Session = Depends(get_db),
) -> list[dict]:
    runs = persistence.list_agent_runs(db)
    payload: list[dict] = []
    for run in runs:
        tools = [tc.tool_name for tc in run.tool_calls]
        first_tool = tools[0] if tools else "none"
        first_output = ""
        first_input = run.input_text
        if run.tool_calls:
            first_output = run.tool_calls[0].output_json or ""
        payload.append(
            {
                "id": run.id,
                "input": run.input_text[:80],
                "intent": run.intent,
                "action": "escalate" if run.status.value == "escalated" else "respond",
                "tool": first_tool,
                "confidence": int(round(run.confidence * 100)),
                "latency": f"{run.latency_ms} ms",
                "status": run.status.value,
                "details": {
                    "userInput": run.input_text,
                    "detectedIntent": run.intent,
                    "agentDecision": (
                        "Escalated to human" if run.status.value == "escalated" else "Resolved with tools"
                    ),
                    "knowledgeRetrieved": ", ".join(
                        t for t in tools if t == "search_knowledge_base"
                    )
                    or "none",
                    "toolCalls": ", ".join(tools) or "none",
                    "toolInput": first_input[:200],
                    "toolOutput": first_output[:300],
                    "finalResponse": run.output_text,
                    "executionTime": f"{run.latency_ms} ms",
                },
            }
        )
    return payload


@router.get("/agent-runs/stats")
def agent_run_stats(
    _: User = Depends(require_support_or_admin),
    db: Session = Depends(get_db),
) -> dict:
    runs = persistence.list_agent_runs(db, limit=500)
    total = len(runs)
    escalated = sum(1 for r in runs if r.status.value == "escalated")
    success = sum(1 for r in runs if r.status.value == "success")
    avg_latency = int(sum(r.latency_ms for r in runs) / total) if total else 0
    return {
        "total": total,
        "success": success,
        "escalated": escalated,
        "avgLatencyMs": avg_latency,
    }
