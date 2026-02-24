"""
Knowledge Base Service
RAG implementation using pgvector for semantic search
"""

import hashlib
import re
from typing import Any
from uuid import UUID

import httpx
import structlog
from sqlalchemy import and_, delete, func, select, text
from sqlalchemy.dialects.postgresql import insert

from app.core.config import settings
from app.db.models import KnowledgeBase, KnowledgeChunk
from app.db.session import AsyncSession

logger = structlog.get_logger()


class KnowledgeService:
    """
    Manages knowledge bases for RAG retrieval.
    
    Features:
    - Document ingestion and chunking
    - OpenAI embedding generation
    - Semantic search with pgvector
    - Per-client namespace isolation
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_model = settings.openai_embedding_model
        self.chunk_size = 500  # tokens (approximate)
        self.chunk_overlap = 50  # tokens
        self.similarity_threshold = 0.75
        self.max_results = 3

    # =========================================================================
    # Knowledge Base CRUD
    # =========================================================================

    async def create_knowledge_base(
        self,
        client_id: UUID,
        name: str,
        description: str | None = None,
    ) -> KnowledgeBase:
        """Create a new knowledge base for a client."""
        kb = KnowledgeBase(
            client_id=client_id,
            name=name,
            description=description,
            is_active=True,
        )
        self.db.add(kb)
        await self.db.commit()
        await self.db.refresh(kb)
        
        logger.info(
            "Knowledge base created",
            kb_id=str(kb.id),
            client_id=str(client_id),
            name=name,
        )
        return kb

    async def get_knowledge_base(self, kb_id: UUID) -> KnowledgeBase | None:
        """Get a knowledge base by ID."""
        result = await self.db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        )
        return result.scalar_one_or_none()

    async def list_knowledge_bases(self, client_id: UUID) -> list[KnowledgeBase]:
        """List all knowledge bases for a client."""
        result = await self.db.execute(
            select(KnowledgeBase)
            .where(KnowledgeBase.client_id == client_id)
            .order_by(KnowledgeBase.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete_knowledge_base(self, kb_id: UUID) -> bool:
        """Delete a knowledge base and all its chunks."""
        # Delete chunks first
        await self.db.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.knowledge_base_id == kb_id)
        )
        
        # Delete knowledge base
        result = await self.db.execute(
            delete(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        )
        await self.db.commit()
        
        return result.rowcount > 0

    # =========================================================================
    # Document Ingestion
    # =========================================================================

    async def ingest_document(
        self,
        kb_id: UUID,
        content: str,
        source: str,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """
        Ingest a document into the knowledge base.
        
        Args:
            kb_id: Knowledge base ID
            content: Document text content
            source: Source identifier (filename, URL, etc.)
            metadata: Optional metadata to attach to chunks
            
        Returns:
            Number of chunks created
        """
        # Get knowledge base
        kb = await self.get_knowledge_base(kb_id)
        if not kb:
            raise ValueError(f"Knowledge base {kb_id} not found")

        # Chunk the document
        chunks = self._chunk_text(content)
        
        if not chunks:
            logger.warning("No chunks generated from document", source=source)
            return 0

        # Generate embeddings for all chunks
        embeddings = await self._generate_embeddings([c["text"] for c in chunks])
        
        if len(embeddings) != len(chunks):
            raise ValueError("Embedding count mismatch")

        # Insert chunks with embeddings
        chunk_count = 0
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            # Generate content hash for deduplication
            content_hash = hashlib.sha256(chunk["text"].encode()).hexdigest()[:32]
            
            chunk_obj = KnowledgeChunk(
                knowledge_base_id=kb_id,
                content=chunk["text"],
                content_hash=content_hash,
                embedding=embedding,
                source=source,
                chunk_index=i,
                token_count=len(chunk["text"].split()),
                chunk_metadata=metadata or {},
            )
            self.db.add(chunk_obj)
            chunk_count += 1

        # Update document count on knowledge base
        kb.document_count = (kb.document_count or 0) + 1
        
        await self.db.commit()
        
        logger.info(
            "Document ingested",
            kb_id=str(kb_id),
            source=source,
            chunk_count=chunk_count,
        )
        
        return chunk_count

    async def ingest_faq(
        self,
        kb_id: UUID,
        question: str,
        answer: str,
        category: str | None = None,
    ) -> int:
        """
        Ingest a single FAQ item.
        Stores as a single chunk with Q&A format.
        """
        content = f"Question: {question}\n\nAnswer: {answer}"
        metadata = {"type": "faq", "category": category} if category else {"type": "faq"}
        
        return await self.ingest_document(
            kb_id=kb_id,
            content=content,
            source="faq",
            metadata=metadata,
        )

    async def bulk_ingest_faqs(
        self,
        kb_id: UUID,
        faqs: list[dict[str, str]],
    ) -> int:
        """
        Bulk ingest multiple FAQs.
        
        Args:
            kb_id: Knowledge base ID
            faqs: List of {"question": str, "answer": str, "category": str?}
            
        Returns:
            Total chunks created
        """
        total_chunks = 0
        for faq in faqs:
            chunks = await self.ingest_faq(
                kb_id=kb_id,
                question=faq["question"],
                answer=faq["answer"],
                category=faq.get("category"),
            )
            total_chunks += chunks
        
        return total_chunks

    # =========================================================================
    # Semantic Search (RAG Retrieval)
    # =========================================================================

    async def search(
        self,
        client_id: UUID,
        query: str,
        kb_ids: list[UUID] | None = None,
        max_results: int | None = None,
        similarity_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search knowledge bases using semantic similarity.
        
        Args:
            client_id: Client ID for namespace isolation
            query: Search query
            kb_ids: Optional list of specific knowledge base IDs to search
            max_results: Maximum number of results (default: 3)
            similarity_threshold: Minimum similarity score (default: 0.75)
            
        Returns:
            List of matching chunks with scores
        """
        max_results = max_results or self.max_results
        threshold = similarity_threshold or self.similarity_threshold

        # Generate query embedding
        query_embeddings = await self._generate_embeddings([query])
        if not query_embeddings:
            logger.error("Failed to generate query embedding")
            return []
        
        query_embedding = query_embeddings[0]

        # Build the query
        # Using pgvector's <=> operator for cosine distance
        # Cosine similarity = 1 - cosine distance
        
        # Format the embedding vector as a pgvector-compatible string
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
        
        # Use CAST() instead of :: to avoid asyncpg parameter syntax conflicts
        query_sql = """
        SELECT 
            kc.id,
            kc.content,
            kc.source,
            kc.metadata,
            kc.chunk_index,
            kb.name as kb_name,
            1 - (kc.embedding <=> CAST(:query_embedding AS vector)) as similarity
        FROM knowledge_chunks kc
        JOIN knowledge_bases kb ON kc.knowledge_base_id = kb.id
        WHERE kb.client_id = :client_id
        AND kb.is_active = true
        AND kc.is_active = true
        """
        
        params: dict[str, Any] = {
            "client_id": str(client_id),
            "query_embedding": embedding_str,
        }
        
        if kb_ids:
            query_sql += " AND kb.id = ANY(:kb_ids)"
            params["kb_ids"] = [str(kb_id) for kb_id in kb_ids]
        
        query_sql += """
        AND 1 - (kc.embedding <=> CAST(:query_embedding AS vector)) >= :threshold
        ORDER BY kc.embedding <=> CAST(:query_embedding AS vector)
        LIMIT :max_results
        """
        params["threshold"] = threshold
        params["max_results"] = max_results
        
        result = await self.db.execute(text(query_sql), params)
        rows = result.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "id": str(row.id),
                "content": row.content,
                "source": row.source,
                "metadata": row.metadata,
                "chunk_index": row.chunk_index,
                "knowledge_base": row.kb_name,
                "similarity": float(row.similarity),
            })
        
        logger.debug(
            "Knowledge search completed",
            client_id=str(client_id),
            query_length=len(query),
            results_count=len(results),
        )
        
        return results

    async def get_context_for_conversation(
        self,
        client_id: UUID,
        messages: list[str],
        max_results: int = 3,
    ) -> str:
        """
        Get relevant context for a conversation.
        Combines recent messages into a query for better retrieval.
        
        Args:
            client_id: Client ID
            messages: Recent messages from conversation
            max_results: Maximum chunks to retrieve
            
        Returns:
            Formatted context string for injection into prompt
        """
        # Combine last few messages for context
        query = " ".join(messages[-3:])[:500]  # Limit query length
        
        results = await self.search(
            client_id=client_id,
            query=query,
            max_results=max_results,
        )
        
        if not results:
            return ""
        
        # Format context for prompt injection
        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(
                f"[Context {i} - {result['knowledge_base']}]\n{result['content']}"
            )
        
        return "\n\n".join(context_parts)

    # =========================================================================
    # Private Methods
    # =========================================================================

    def _chunk_text(self, text: str) -> list[dict[str, Any]]:
        """
        Split text into overlapping chunks.
        
        Uses a simple sentence-based chunking strategy:
        1. Split into sentences
        2. Group sentences until chunk size reached
        3. Add overlap from previous chunk
        """
        # Clean text
        text = text.strip()
        if not text:
            return []
        
        # Split into sentences (simple regex)
        sentence_pattern = r'(?<=[.!?])\s+'
        sentences = re.split(sentence_pattern, text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return [{"text": text, "start": 0, "end": len(text)}]
        
        chunks = []
        current_chunk: list[str] = []
        current_length = 0
        
        # Approximate tokens as words / 0.75
        def estimate_tokens(s: str) -> int:
            return int(len(s.split()) / 0.75)
        
        for sentence in sentences:
            sentence_tokens = estimate_tokens(sentence)
            
            if current_length + sentence_tokens > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = " ".join(current_chunk)
                chunks.append({"text": chunk_text})
                
                # Start new chunk with overlap
                overlap_sentences = []
                overlap_length = 0
                for s in reversed(current_chunk):
                    s_tokens = estimate_tokens(s)
                    if overlap_length + s_tokens <= self.chunk_overlap:
                        overlap_sentences.insert(0, s)
                        overlap_length += s_tokens
                    else:
                        break
                
                current_chunk = overlap_sentences
                current_length = overlap_length
            
            current_chunk.append(sentence)
            current_length += sentence_tokens
        
        # Don't forget the last chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append({"text": chunk_text})
        
        return chunks

    async def _generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings using OpenAI's API.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured")
        
        api_key = settings.openai_api_key.get_secret_value()
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.embedding_model,
                        "input": texts,
                    },
                )
                response.raise_for_status()
                data = response.json()
                
                # Sort by index to maintain order
                embeddings_data = sorted(data["data"], key=lambda x: x["index"])
                embeddings = [item["embedding"] for item in embeddings_data]
                
                logger.debug(
                    "Embeddings generated",
                    count=len(embeddings),
                    model=self.embedding_model,
                )
                
                return embeddings
                
        except httpx.HTTPError as e:
            logger.error("Failed to generate embeddings", error=str(e))
            raise

    # =========================================================================
    # Maintenance
    # =========================================================================

    async def get_chunk_count(self, kb_id: UUID) -> int:
        """Get the number of chunks in a knowledge base."""
        result = await self.db.execute(
            select(func.count(KnowledgeChunk.id))
            .where(KnowledgeChunk.knowledge_base_id == kb_id)
        )
        return result.scalar() or 0

    async def clear_knowledge_base(self, kb_id: UUID) -> int:
        """Delete all chunks from a knowledge base."""
        result = await self.db.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.knowledge_base_id == kb_id)
        )
        
        # Reset document count
        kb = await self.get_knowledge_base(kb_id)
        if kb:
            kb.document_count = 0
        
        await self.db.commit()
        
        return result.rowcount
