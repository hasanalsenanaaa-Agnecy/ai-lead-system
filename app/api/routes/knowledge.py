"""
Knowledge Base API Routes
Manage knowledge bases and document ingestion for RAG
"""

from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.db.session import AsyncSession, get_db
from app.services.knowledge_service import KnowledgeService

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/knowledge", tags=["Knowledge Base"])


# =============================================================================
# Request/Response Models
# =============================================================================


class KnowledgeBaseCreate(BaseModel):
    """Create knowledge base request."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None


class KnowledgeBaseResponse(BaseModel):
    """Knowledge base response."""
    id: str
    client_id: str
    name: str
    description: str | None
    document_count: int
    is_active: bool
    created_at: str
    
    class Config:
        from_attributes = True


class DocumentIngestRequest(BaseModel):
    """Document ingestion request."""
    content: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1, max_length=255)
    metadata: dict[str, Any] | None = None


class FAQIngestRequest(BaseModel):
    """FAQ ingestion request."""
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    category: str | None = None


class BulkFAQIngestRequest(BaseModel):
    """Bulk FAQ ingestion request."""
    faqs: list[FAQIngestRequest] = Field(..., min_items=1)


class SearchRequest(BaseModel):
    """Knowledge base search request."""
    query: str = Field(..., min_length=1)
    kb_ids: list[str] | None = None
    max_results: int = Field(default=3, ge=1, le=10)
    similarity_threshold: float = Field(default=0.75, ge=0.0, le=1.0)


class SearchResult(BaseModel):
    """Search result item."""
    id: str
    content: str
    source: str
    metadata: dict[str, Any]
    knowledge_base: str
    similarity: float


class SearchResponse(BaseModel):
    """Search response."""
    results: list[SearchResult]
    query: str


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/bases", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    client_id: UUID,
    request: KnowledgeBaseCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new knowledge base for a client."""
    service = KnowledgeService(db)
    
    kb = await service.create_knowledge_base(
        client_id=client_id,
        name=request.name,
        description=request.description,
    )
    
    return KnowledgeBaseResponse(
        id=str(kb.id),
        client_id=str(kb.client_id),
        name=kb.name,
        description=kb.description,
        document_count=kb.document_count or 0,
        is_active=kb.is_active,
        created_at=kb.created_at.isoformat(),
    )


@router.get("/bases/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get knowledge base details."""
    service = KnowledgeService(db)
    
    kb = await service.get_knowledge_base(kb_id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )
    
    return KnowledgeBaseResponse(
        id=str(kb.id),
        client_id=str(kb.client_id),
        name=kb.name,
        description=kb.description,
        document_count=kb.document_count or 0,
        is_active=kb.is_active,
        created_at=kb.created_at.isoformat(),
    )


@router.get("/client/{client_id}/bases", response_model=list[KnowledgeBaseResponse])
async def list_knowledge_bases(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """List all knowledge bases for a client."""
    service = KnowledgeService(db)
    
    kbs = await service.list_knowledge_bases(client_id)
    
    return [
        KnowledgeBaseResponse(
            id=str(kb.id),
            client_id=str(kb.client_id),
            name=kb.name,
            description=kb.description,
            document_count=kb.document_count or 0,
            is_active=kb.is_active,
            created_at=kb.created_at.isoformat(),
        )
        for kb in kbs
    ]


@router.delete("/bases/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base(
    kb_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a knowledge base and all its chunks."""
    service = KnowledgeService(db)
    
    deleted = await service.delete_knowledge_base(kb_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )


@router.post("/bases/{kb_id}/documents")
async def ingest_document(
    kb_id: UUID,
    request: DocumentIngestRequest,
    db: AsyncSession = Depends(get_db),
):
    """Ingest a document into the knowledge base."""
    service = KnowledgeService(db)
    
    try:
        chunk_count = await service.ingest_document(
            kb_id=kb_id,
            content=request.content,
            source=request.source,
            metadata=request.metadata,
        )
        
        return {
            "status": "success",
            "chunks_created": chunk_count,
            "knowledge_base_id": str(kb_id),
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/bases/{kb_id}/faqs")
async def ingest_faq(
    kb_id: UUID,
    request: FAQIngestRequest,
    db: AsyncSession = Depends(get_db),
):
    """Ingest a single FAQ item."""
    service = KnowledgeService(db)
    
    try:
        chunk_count = await service.ingest_faq(
            kb_id=kb_id,
            question=request.question,
            answer=request.answer,
            category=request.category,
        )
        
        return {
            "status": "success",
            "chunks_created": chunk_count,
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/bases/{kb_id}/faqs/bulk")
async def bulk_ingest_faqs(
    kb_id: UUID,
    request: BulkFAQIngestRequest,
    db: AsyncSession = Depends(get_db),
):
    """Bulk ingest multiple FAQs."""
    service = KnowledgeService(db)
    
    try:
        faqs = [
            {
                "question": faq.question,
                "answer": faq.answer,
                "category": faq.category,
            }
            for faq in request.faqs
        ]
        
        total_chunks = await service.bulk_ingest_faqs(
            kb_id=kb_id,
            faqs=faqs,
        )
        
        return {
            "status": "success",
            "faqs_processed": len(faqs),
            "total_chunks_created": total_chunks,
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/search", response_model=SearchResponse)
async def search_knowledge_base(
    client_id: UUID,
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Search knowledge bases using semantic similarity."""
    service = KnowledgeService(db)
    
    kb_ids = [UUID(kb_id) for kb_id in request.kb_ids] if request.kb_ids else None
    
    results = await service.search(
        client_id=client_id,
        query=request.query,
        kb_ids=kb_ids,
        max_results=request.max_results,
        similarity_threshold=request.similarity_threshold,
    )
    
    return SearchResponse(
        results=[
            SearchResult(
                id=r["id"],
                content=r["content"],
                source=r["source"],
                metadata=r["metadata"],
                knowledge_base=r["knowledge_base"],
                similarity=r["similarity"],
            )
            for r in results
        ],
        query=request.query,
    )


@router.get("/bases/{kb_id}/stats")
async def get_knowledge_base_stats(
    kb_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get statistics for a knowledge base."""
    service = KnowledgeService(db)
    
    kb = await service.get_knowledge_base(kb_id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )
    
    chunk_count = await service.get_chunk_count(kb_id)
    
    return {
        "knowledge_base_id": str(kb_id),
        "name": kb.name,
        "document_count": kb.document_count or 0,
        "chunk_count": chunk_count,
        "is_active": kb.is_active,
    }


@router.post("/bases/{kb_id}/clear", status_code=status.HTTP_200_OK)
async def clear_knowledge_base(
    kb_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Clear all chunks from a knowledge base."""
    service = KnowledgeService(db)
    
    deleted_count = await service.clear_knowledge_base(kb_id)
    
    return {
        "status": "success",
        "chunks_deleted": deleted_count,
    }
