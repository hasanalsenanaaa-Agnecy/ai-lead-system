"""
RAG (Retrieval Augmented Generation) Service.
Handles knowledge base embeddings and similarity search.
"""
import uuid
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

import openai
from openai import AsyncOpenAI
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.config import settings
from app.models.models import KnowledgeBaseEntry

logger = structlog.get_logger()


@dataclass
class RetrievalResult:
    """Result from knowledge base retrieval."""
    id: uuid.UUID
    title: str
    content: str
    category: Optional[str]
    similarity_score: float


class RAGService:
    """
    RAG Service for knowledge base management and retrieval.
    Uses OpenAI embeddings for vector search.
    """
    
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.embedding_model = settings.OPENAI_EMBEDDING_MODEL
        self.embedding_dimensions = 1536
        self.default_top_k = 3
        self.chunk_size = 500  # tokens
        self.chunk_overlap = 50  # tokens
    
    async def create_embedding(self, text: str) -> List[float]:
        """
        Create embedding vector for text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector (1536 dimensions)
        """
        try:
            response = await self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error("Failed to create embedding", error=str(e))
            raise
    
    async def add_knowledge_entry(
        self,
        db: AsyncSession,
        client_id: uuid.UUID,
        title: str,
        content: str,
        category: Optional[str] = None,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> KnowledgeBaseEntry:
        """
        Add a new knowledge base entry with embedding.
        
        Args:
            db: Database session
            client_id: Client tenant ID
            title: Entry title
            content: Entry content
            category: Optional category
            source: Optional source reference
            metadata: Optional additional metadata
            
        Returns:
            Created knowledge base entry
        """
        # Combine title and content for embedding
        text_for_embedding = f"{title}\n\n{content}"
        
        # Create embedding
        embedding = await self.create_embedding(text_for_embedding)
        
        # Create entry
        entry = KnowledgeBaseEntry(
            client_id=client_id,
            title=title,
            content=content,
            category=category,
            source=source,
            metadata=metadata,
            embedding=embedding,
            is_active=True
        )
        
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        
        logger.info("Added knowledge base entry", entry_id=str(entry.id), title=title)
        return entry
    
    async def update_knowledge_entry(
        self,
        db: AsyncSession,
        entry_id: uuid.UUID,
        title: Optional[str] = None,
        content: Optional[str] = None,
        category: Optional[str] = None
    ) -> Optional[KnowledgeBaseEntry]:
        """
        Update a knowledge base entry and re-embed if content changed.
        """
        result = await db.execute(
            select(KnowledgeBaseEntry).where(KnowledgeBaseEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        
        if not entry:
            return None
        
        # Track if we need to re-embed
        needs_reembed = False
        
        if title is not None and title != entry.title:
            entry.title = title
            needs_reembed = True
        
        if content is not None and content != entry.content:
            entry.content = content
            needs_reembed = True
        
        if category is not None:
            entry.category = category
        
        # Re-embed if content changed
        if needs_reembed:
            text_for_embedding = f"{entry.title}\n\n{entry.content}"
            entry.embedding = await self.create_embedding(text_for_embedding)
        
        await db.commit()
        await db.refresh(entry)
        
        return entry
    
    async def delete_knowledge_entry(
        self,
        db: AsyncSession,
        entry_id: uuid.UUID
    ) -> bool:
        """Delete a knowledge base entry."""
        result = await db.execute(
            select(KnowledgeBaseEntry).where(KnowledgeBaseEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        
        if not entry:
            return False
        
        await db.delete(entry)
        await db.commit()
        return True
    
    async def search_knowledge_base(
        self,
        db: AsyncSession,
        client_id: uuid.UUID,
        query: str,
        top_k: int = 3,
        category: Optional[str] = None,
        similarity_threshold: float = 0.7
    ) -> List[RetrievalResult]:
        """
        Search knowledge base using vector similarity.
        
        Args:
            db: Database session
            client_id: Client tenant ID
            query: Search query
            top_k: Number of results to return
            category: Optional category filter
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of retrieval results sorted by similarity
        """
        try:
            # Create query embedding
            query_embedding = await self.create_embedding(query)
            
            # Build the similarity search query
            # Using pgvector's <=> operator for cosine distance
            # Cosine similarity = 1 - cosine distance
            
            embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"
            
            # Build base query
            sql = f"""
                SELECT 
                    id,
                    title,
                    content,
                    category,
                    1 - (embedding <=> '{embedding_str}'::vector) as similarity
                FROM knowledge_base
                WHERE client_id = :client_id
                AND is_active = true
                AND embedding IS NOT NULL
            """
            
            params = {"client_id": client_id}
            
            # Add category filter if provided
            if category:
                sql += " AND category = :category"
                params["category"] = category
            
            # Add similarity threshold and ordering
            sql += f"""
                AND 1 - (embedding <=> '{embedding_str}'::vector) >= :threshold
                ORDER BY similarity DESC
                LIMIT :limit
            """
            params["threshold"] = similarity_threshold
            params["limit"] = top_k
            
            # Execute query
            result = await db.execute(text(sql), params)
            rows = result.fetchall()
            
            # Convert to RetrievalResult objects
            results = [
                RetrievalResult(
                    id=row[0],
                    title=row[1],
                    content=row[2],
                    category=row[3],
                    similarity_score=float(row[4])
                )
                for row in rows
            ]
            
            logger.info(
                "Knowledge base search completed",
                client_id=str(client_id),
                query_length=len(query),
                results_found=len(results)
            )
            
            return results
            
        except Exception as e:
            logger.error("Knowledge base search failed", error=str(e))
            return []
    
    async def get_context_for_conversation(
        self,
        db: AsyncSession,
        client_id: uuid.UUID,
        message: str,
        top_k: int = 3
    ) -> str:
        """
        Get relevant context from knowledge base for a conversation.
        Returns formatted string suitable for inclusion in AI prompt.
        
        Args:
            db: Database session
            client_id: Client tenant ID
            message: User message to find context for
            top_k: Number of context items to retrieve
            
        Returns:
            Formatted context string
        """
        results = await self.search_knowledge_base(
            db=db,
            client_id=client_id,
            query=message,
            top_k=top_k,
            similarity_threshold=0.65
        )
        
        if not results:
            return ""
        
        context_parts = []
        for result in results:
            context_parts.append(f"### {result.title}\n{result.content}")
        
        return "\n\n".join(context_parts)
    
    async def bulk_import_knowledge(
        self,
        db: AsyncSession,
        client_id: uuid.UUID,
        entries: List[Dict[str, Any]]
    ) -> int:
        """
        Bulk import knowledge base entries.
        
        Args:
            db: Database session
            client_id: Client tenant ID
            entries: List of entry dicts with title, content, category, source
            
        Returns:
            Number of entries successfully imported
        """
        imported = 0
        
        for entry in entries:
            try:
                await self.add_knowledge_entry(
                    db=db,
                    client_id=client_id,
                    title=entry.get("title", "Untitled"),
                    content=entry.get("content", ""),
                    category=entry.get("category"),
                    source=entry.get("source"),
                    metadata=entry.get("metadata")
                )
                imported += 1
            except Exception as e:
                logger.error(
                    "Failed to import knowledge entry",
                    title=entry.get("title"),
                    error=str(e)
                )
        
        logger.info(
            "Bulk knowledge import completed",
            client_id=str(client_id),
            total_entries=len(entries),
            imported=imported
        )
        
        return imported


# Chunking utilities for large documents
class TextChunker:
    """Utility for chunking large texts for embedding."""
    
    @staticmethod
    def chunk_text(
        text: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Text to chunk
            chunk_size: Approximate size of each chunk (in words)
            chunk_overlap: Number of words to overlap between chunks
            
        Returns:
            List of text chunks
        """
        words = text.split()
        chunks = []
        
        if len(words) <= chunk_size:
            return [text]
        
        start = 0
        while start < len(words):
            end = start + chunk_size
            chunk = " ".join(words[start:end])
            chunks.append(chunk)
            
            # Move start position with overlap
            start = end - chunk_overlap
            
            # Prevent infinite loop on small texts
            if start >= len(words) - chunk_overlap:
                break
        
        return chunks
    
    @staticmethod
    def chunk_document(
        title: str,
        content: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> List[Dict[str, str]]:
        """
        Chunk a document into multiple entries.
        
        Returns:
            List of dicts with title and content for each chunk
        """
        chunks = TextChunker.chunk_text(content, chunk_size, chunk_overlap)
        
        result = []
        for i, chunk in enumerate(chunks):
            chunk_title = title if len(chunks) == 1 else f"{title} (Part {i + 1})"
            result.append({
                "title": chunk_title,
                "content": chunk
            })
        
        return result


# Export singleton instance
rag_service = RAGService()
text_chunker = TextChunker()
