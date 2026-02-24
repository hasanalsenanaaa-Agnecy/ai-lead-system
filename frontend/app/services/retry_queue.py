"""
Retry Queue Service
Handles failed operations with exponential backoff
"""

import asyncio
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Optional
from uuid import UUID, uuid4

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD = "dead"  # Max retries exceeded


@dataclass
class RetryTask:
    """A task in the retry queue."""
    id: str
    task_type: str
    payload: Dict[str, Any]
    status: TaskStatus
    attempts: int
    max_attempts: int
    created_at: str
    next_retry_at: str
    last_error: Optional[str] = None
    completed_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "RetryTask":
        data['status'] = TaskStatus(data['status'])
        return cls(**data)


class RetryQueue:
    """
    Async retry queue using Redis.
    Supports exponential backoff and dead letter queue.
    """
    
    # Backoff configuration
    BASE_DELAY_SECONDS = 30
    MAX_DELAY_SECONDS = 3600  # 1 hour max
    BACKOFF_MULTIPLIER = 2
    
    # Queue keys
    PENDING_QUEUE = "retry:pending"
    PROCESSING_SET = "retry:processing"
    DEAD_LETTER_QUEUE = "retry:dead"
    TASK_PREFIX = "retry:task:"
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._handlers: Dict[str, Callable] = {}
    
    async def connect(self):
        """Connect to Redis."""
        if not self._redis:
            self._redis = redis.from_url(settings.redis_url)
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None
    
    def register_handler(self, task_type: str, handler: Callable):
        """Register a handler for a task type."""
        self._handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type}")
    
    async def enqueue(
        self,
        task_type: str,
        payload: Dict[str, Any],
        max_attempts: int = 5,
        delay_seconds: int = 0,
    ) -> str:
        """
        Add a task to the retry queue.
        Returns task ID.
        """
        await self.connect()
        
        task_id = str(uuid4())
        now = datetime.utcnow()
        next_retry = now + timedelta(seconds=delay_seconds)
        
        task = RetryTask(
            id=task_id,
            task_type=task_type,
            payload=payload,
            status=TaskStatus.PENDING,
            attempts=0,
            max_attempts=max_attempts,
            created_at=now.isoformat(),
            next_retry_at=next_retry.isoformat(),
        )
        
        # Store task data
        await self._redis.set(
            f"{self.TASK_PREFIX}{task_id}",
            json.dumps(task.to_dict()),
            ex=86400 * 7,  # 7 day TTL
        )
        
        # Add to pending queue with score = next_retry timestamp
        await self._redis.zadd(
            self.PENDING_QUEUE,
            {task_id: next_retry.timestamp()},
        )
        
        logger.info(f"Enqueued task {task_id} of type {task_type}")
        return task_id
    
    async def get_task(self, task_id: str) -> Optional[RetryTask]:
        """Get a task by ID."""
        await self.connect()
        
        data = await self._redis.get(f"{self.TASK_PREFIX}{task_id}")
        if data:
            return RetryTask.from_dict(json.loads(data))
        return None
    
    async def process_pending(self) -> int:
        """
        Process all pending tasks that are ready.
        Returns number of tasks processed.
        """
        await self.connect()
        
        now = datetime.utcnow()
        processed = 0
        
        # Get tasks ready for retry
        task_ids = await self._redis.zrangebyscore(
            self.PENDING_QUEUE,
            0,
            now.timestamp(),
            start=0,
            num=100,
        )
        
        for task_id_bytes in task_ids:
            task_id = task_id_bytes.decode() if isinstance(task_id_bytes, bytes) else task_id_bytes
            
            # Move to processing
            await self._redis.zrem(self.PENDING_QUEUE, task_id)
            await self._redis.sadd(self.PROCESSING_SET, task_id)
            
            try:
                await self._process_task(task_id)
                processed += 1
            except Exception as e:
                logger.error(f"Error processing task {task_id}: {e}")
            finally:
                await self._redis.srem(self.PROCESSING_SET, task_id)
        
        return processed
    
    async def _process_task(self, task_id: str):
        """Process a single task."""
        task = await self.get_task(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found")
            return
        
        handler = self._handlers.get(task.task_type)
        if not handler:
            logger.error(f"No handler for task type: {task.task_type}")
            return
        
        task.attempts += 1
        task.status = TaskStatus.PROCESSING
        
        try:
            # Execute the handler
            await handler(task.payload)
            
            # Success
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow().isoformat()
            
            logger.info(f"Task {task_id} completed successfully")
            
        except Exception as e:
            task.last_error = str(e)
            logger.warning(f"Task {task_id} failed (attempt {task.attempts}): {e}")
            
            if task.attempts >= task.max_attempts:
                # Move to dead letter queue
                task.status = TaskStatus.DEAD
                await self._redis.lpush(self.DEAD_LETTER_QUEUE, task_id)
                logger.error(f"Task {task_id} moved to dead letter queue after {task.attempts} attempts")
            else:
                # Schedule retry with exponential backoff
                delay = min(
                    self.BASE_DELAY_SECONDS * (self.BACKOFF_MULTIPLIER ** (task.attempts - 1)),
                    self.MAX_DELAY_SECONDS
                )
                next_retry = datetime.utcnow() + timedelta(seconds=delay)
                task.next_retry_at = next_retry.isoformat()
                task.status = TaskStatus.PENDING
                
                await self._redis.zadd(
                    self.PENDING_QUEUE,
                    {task_id: next_retry.timestamp()},
                )
                logger.info(f"Task {task_id} scheduled for retry in {delay}s")
        
        # Update task data
        await self._redis.set(
            f"{self.TASK_PREFIX}{task_id}",
            json.dumps(task.to_dict()),
            ex=86400 * 7,
        )
    
    async def get_queue_stats(self) -> dict:
        """Get queue statistics."""
        await self.connect()
        
        pending = await self._redis.zcard(self.PENDING_QUEUE)
        processing = await self._redis.scard(self.PROCESSING_SET)
        dead = await self._redis.llen(self.DEAD_LETTER_QUEUE)
        
        return {
            "pending": pending,
            "processing": processing,
            "dead_letter": dead,
        }
    
    async def retry_dead_letter(self, task_id: str) -> bool:
        """Retry a task from the dead letter queue."""
        await self.connect()
        
        task = await self.get_task(task_id)
        if not task or task.status != TaskStatus.DEAD:
            return False
        
        # Remove from dead letter queue
        await self._redis.lrem(self.DEAD_LETTER_QUEUE, 1, task_id)
        
        # Reset and re-enqueue
        task.status = TaskStatus.PENDING
        task.attempts = 0
        task.next_retry_at = datetime.utcnow().isoformat()
        
        await self._redis.set(
            f"{self.TASK_PREFIX}{task_id}",
            json.dumps(task.to_dict()),
            ex=86400 * 7,
        )
        
        await self._redis.zadd(
            self.PENDING_QUEUE,
            {task_id: datetime.utcnow().timestamp()},
        )
        
        logger.info(f"Task {task_id} moved from dead letter queue to pending")
        return True


# Global instance
retry_queue = RetryQueue()


# Background worker
async def retry_worker():
    """Background worker to process retry queue."""
    logger.info("Retry worker started")
    
    while True:
        try:
            processed = await retry_queue.process_pending()
            if processed > 0:
                logger.info(f"Processed {processed} retry tasks")
        except Exception as e:
            logger.error(f"Retry worker error: {e}")
        
        await asyncio.sleep(10)  # Check every 10 seconds
