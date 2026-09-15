"""Asynchronous in-memory event bus for continuous non-blocking event streaming."""
import asyncio
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("sentinel.streaming")

# Primary in-memory queue for streaming access events
event_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=20000)


async def publish_event(event_data: Dict[str, Any]) -> bool:
    """Non-blocking publish of an access event to the streaming queue."""
    try:
        event_queue.put_nowait(event_data)
        return True
    except asyncio.QueueFull:
        logger.warning("Streaming event queue is full! Dropping oldest or failing enqueue.")
        try:
            # Drop oldest event to maintain freshness in extreme load
            _ = event_queue.get_nowait()
            event_queue.put_nowait(event_data)
            return True
        except Exception as e:
            logger.error(f"Failed to enqueue event: {e}")
            return False


async def get_next_event() -> Dict[str, Any]:
    """Retrieve next event from the continuous streaming queue."""
    return await event_queue.get()


def get_queue_size() -> int:
    """Return the current number of events pending in the queue."""
    return event_queue.qsize()
