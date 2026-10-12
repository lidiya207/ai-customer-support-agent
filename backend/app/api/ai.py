from fastapi import APIRouter

from app.services.llm_service import check_ollama_status

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/status")
async def ai_status() -> dict[str, str]:
    """Report whether the local Ollama provider is reachable."""
    return await check_ollama_status()
