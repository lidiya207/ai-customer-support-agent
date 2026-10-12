"""Knowledge base admin APIs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin, require_support_or_admin
from app.database.session import get_db
from app.models.knowledge import DocumentType, KnowledgeDocument
from app.models.user import User
from app.rag.extract import extract_text_from_upload
from app.rag.knowledge import index_document, search_knowledge

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/documents")
def list_documents(
    _: User = Depends(require_support_or_admin),
    db: Session = Depends(get_db),
) -> list[dict]:
    docs = list(
        db.scalars(select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc()))
    )
    return [
        {
            "id": doc.id,
            "name": doc.name,
            "type": doc.doc_type.value,
            "chunks": doc.chunk_count,
            "status": doc.status.value,
            "uploadedAt": doc.created_at.strftime("%b %d, %Y"),
        }
        for doc in docs
    ]


@router.get("/stats")
def knowledge_stats(
    _: User = Depends(require_support_or_admin),
    db: Session = Depends(get_db),
) -> dict:
    docs = list(db.scalars(select(KnowledgeDocument)))
    return {
        "total": len(docs),
        "indexed": sum(1 for d in docs if d.status.value == "indexed"),
        "processing": sum(1 for d in docs if d.status.value == "processing"),
        "failed": sum(1 for d in docs if d.status.value == "failed"),
        "chunks": sum(d.chunk_count for d in docs),
    }


@router.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form("general"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    filename = file.filename or "document.txt"
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    text, type_name = extract_text_from_upload(filename, raw)
    doc_type = DocumentType[type_name]

    doc = index_document(
        db,
        name=filename,
        content=text,
        category=category,
        doc_type=doc_type,
        uploaded_by=current_user.id,
    )
    return {
        "id": doc.id,
        "name": doc.name,
        "type": doc.doc_type.value,
        "chunks": doc.chunk_count,
        "status": doc.status.value,
        "uploadedAt": doc.created_at.strftime("%b %d, %Y"),
    }


@router.delete("/documents/{document_id}")
def delete_document(
    document_id: str,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    doc = db.get(KnowledgeDocument, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    db.delete(doc)
    db.commit()
    return {"ok": True}


@router.post("/search")
def knowledge_search(
    body: dict,
    _: User = Depends(require_support_or_admin),
    db: Session = Depends(get_db),
) -> dict:
    query = str(body.get("query") or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    return {"results": search_knowledge(query, db=db)}
