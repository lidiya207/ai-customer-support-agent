from pydantic import BaseModel, Field


class ChatHistoryMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Customer message text")
    history: list[ChatHistoryMessage] = Field(default_factory=list)
    conversation_id: str | None = None


class KnowledgeSource(BaseModel):
    document_id: str | None = None
    title: str | None = None
    similarity: float | None = None


class ChatResponse(BaseModel):
    response: str
    model: str | None = None
    intent: str | None = None
    confidence: float | None = None
    tools_used: list[str] = Field(default_factory=list)
    sources: list[KnowledgeSource] = Field(default_factory=list)
    escalated: bool = False
    ticket_id: str | None = None
    conversation_id: str | None = None
