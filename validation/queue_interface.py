import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Optional, Any
from validation.models import TelemetryPayload

logger = logging.getLogger(__name__)

class BaseTelemetryQueue(ABC):
    """Abstract interface for telemetry queues."""
    
    @abstractmethod
    async def put(self, payload: Optional[TelemetryPayload]) -> None:
        """Put a payload into the queue. None acts as a sentinel for shutdown."""
        pass
        
    @abstractmethod
    async def get(self) -> Optional[TelemetryPayload]:
        """Get a payload from the queue. Returns None if it's a sentinel."""
        pass

    @abstractmethod
    async def qsize(self) -> int:
        """Return approximate queue size."""
        pass
        
    @abstractmethod
    def task_done(self) -> None:
        """Indicate that a formerly enqueued task is complete."""
        pass

class InMemoryTelemetryQueue(BaseTelemetryQueue):
    """Standard in-memory queue using asyncio.Queue."""
    
    def __init__(self, maxsize: int = 0):
        self._queue = asyncio.Queue(maxsize=maxsize)
        
    async def put(self, payload: Optional[TelemetryPayload]) -> None:
        await self._queue.put(payload)
        
    async def get(self) -> Optional[TelemetryPayload]:
        return await self._queue.get()
        
    async def qsize(self) -> int:
        return self._queue.qsize()
        
    def task_done(self) -> None:
        self._queue.task_done()

class RedisTelemetryQueue(BaseTelemetryQueue):
    """
    Durable queue using Redis Lists (rpush/blpop).
    Enables horizontal scaling across multiple FastAPI workers and StreamProcessors.
    """
    
    def __init__(self, redis_client: Any, queue_key: str):
        self._redis = redis_client
        self.queue_key = queue_key
        # Track simulated qsize via LLEN
        self._qsize = 0
        
    async def put(self, payload: Optional[TelemetryPayload]) -> None:
        if payload is None:
            # Sentinel: push a special string
            await self._redis.rpush(self.queue_key, "__SENTINEL__")
        else:
            # Serialize Pydantic model to JSON
            await self._redis.rpush(self.queue_key, payload.model_dump_json())
            
    async def get(self) -> Optional[TelemetryPayload]:
        # blpop returns a tuple (key, value)
        result = await self._redis.blpop(self.queue_key, timeout=0)
        if not result:
            return None
            
        _, value = result
        value_str = value.decode('utf-8')
        
        if value_str == "__SENTINEL__":
            return None
            
        try:
            return TelemetryPayload.model_validate_json(value_str)
        except Exception as e:
            logger.error(f"Failed to deserialize payload from Redis: {e}")
            # Instead of crashing, just return a sentinel or drop it? Let's drop it and wait for next
            # Wait, better to recurse to get the next valid item. But to avoid recursion depth issues:
            pass
            
        return await self.get() # Recursively try next item on failure
        
    async def qsize(self) -> int:
        return await self._redis.llen(self.queue_key)
        
    def task_done(self) -> None:
        # Redis Lists blpop removes the item immediately, so no explicit task_done is strictly needed.
        pass
