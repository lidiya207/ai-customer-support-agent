import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.admin import router as admin_router
from app.api.ai import router as ai_router
from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router
from app.api.knowledge import router as knowledge_router
from app.api.notifications import router as notifications_router
from app.api.settings import router as settings_router
from app.api.tickets import router as tickets_router
from app.core.config import get_settings
from app.database.session import SessionLocal
from app.rag.knowledge import ensure_seed_documents, reindex_embeddings
from app.services.llm_service import warm_ollama_model

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    db = SessionLocal()
    try:
        ensure_seed_documents(db)
        reindex_embeddings(db)
    except Exception:
        # DB may not be migrated yet during first boot.
        db.rollback()
    finally:
        db.close()

    # Warm the local model in the background so the first chat is not cold.
    asyncio.create_task(warm_ollama_model())
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(ai_router)
app.include_router(admin_router)
app.include_router(conversations_router)
app.include_router(tickets_router)
app.include_router(knowledge_router)
app.include_router(analytics_router)
app.include_router(settings_router)
app.include_router(notifications_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "AI Customer Support API is running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/health/database")
def health_database() -> dict[str, str]:
    """Verify the application can connect to MySQL and run a simple query."""
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"status": "connected", "database": "mysql"}
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Database connection failed: {exc}",
        ) from exc
    finally:
        db.close()
