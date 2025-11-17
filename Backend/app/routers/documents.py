from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from ..config import get_settings
from ..schemas.knowledge import DocumentSource, KnowledgeSearchResponse
from ..services.storage.knowledge_base import KnowledgeBase
from ..services.storage.redis_store import RedisStore

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def get_knowledge_base(request: Request) -> KnowledgeBase:
    return request.app.state.knowledge_base


def get_document_store() -> RedisStore:
    return RedisStore()


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 120) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        start += chunk_size - overlap
        if start < 0:
            start = 0
    return chunks or [text]


def load_text_from_upload(file_path: Path, content_type: str) -> str:
    if content_type in {"text/plain", "text/markdown", "application/json"}:
        return file_path.read_text(encoding="utf-8")
    if content_type in {"application/pdf"}:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise HTTPException(status_code=500, detail="PDF ingestion requires pypdf") from exc
        reader = PdfReader(str(file_path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text
    raise HTTPException(status_code=415, detail=f"Unsupported content type: {content_type}")


@router.post("/documents", response_model=DocumentSource)
async def upload_document(
    user_id: str = Form(...),
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str | None = Form(None),
    category: str = Form("general"),
    tags_json: str = Form("[]"),
    knowledge_base: KnowledgeBase = Depends(get_knowledge_base),
    store: RedisStore = Depends(get_document_store),
) -> DocumentSource:
    settings = get_settings()
    uploads_dir = settings.uploads_dir
    uploads_dir.mkdir(parents=True, exist_ok=True)

    document_id = str(uuid.uuid4())
    destination = uploads_dir / document_id
    destination.write_bytes(await file.read())

    text_content = load_text_from_upload(destination, file.content_type or "text/plain")
    checksum = KnowledgeBase.compute_checksum(destination.read_bytes())

    tags: list[str] = []
    try:
        tags = json.loads(tags_json)
    except json.JSONDecodeError:
        pass

    source = DocumentSource(
        id=document_id,
        title=title,
        description=description,
        category=category,
        owner_id=user_id,
        size_bytes=destination.stat().st_size,
        content_type=file.content_type or "application/octet-stream",
        original_filename=file.filename,
        tags=tags,
        checksum=checksum,
    )

    chunks = chunk_text(text_content)
    ingested = await knowledge_base.ingest(source, chunks)
    source.status = "indexed" if ingested else "embedding_failed"

    await store.set_json(f"doc:{document_id}", source.model_dump(mode="json"))

    return source


@router.get("/documents", response_model=list[DocumentSource])
async def list_documents(
    user_id: str | None = None,
    store: RedisStore = Depends(get_document_store)
) -> list[DocumentSource]:
    keys = await store.keys("doc:*")
    documents: list[DocumentSource] = []
    for key in keys:
        data = await store.get_json(key)
        if data:
            doc = DocumentSource(**data)
            if user_id is None or doc.owner_id == user_id:
                documents.append(doc)
    documents.sort(key=lambda item: item.uploaded_at, reverse=True)
    return documents


@router.get("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(query: str, knowledge_base: KnowledgeBase = Depends(get_knowledge_base)) -> KnowledgeSearchResponse:
    return await knowledge_base.search(query)
