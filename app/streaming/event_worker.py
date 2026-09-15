"""Continuous streaming worker consuming access events, running detection, and broadcasting."""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from app.streaming.event_bus import get_next_event, get_queue_size
from app.streaming.connection_manager import ws_manager
from app.detection.engine import detection_engine
from app.db.session import async_session_factory
from app.db.models import AccessEvent, Anomaly

logger = logging.getLogger("sentinel.worker")

_worker_task: Optional[asyncio.Task] = None
_is_running = False


async def event_processing_worker():
    """Continuous async loop popping events from queue, evaluating anomalies, and pushing to WS."""
    global _is_running
    logger.info("Real-time streaming event worker started.")
    
    while _is_running:
        try:
            # Non-blocking fetch with timeout so we can check _is_running flag
            try:
                event_data = await asyncio.wait_for(get_next_event(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            # 1. Run detection engine
            flagged = detection_engine.process_event(event_data)

            # 2. Persist AccessEvent and Anomaly records to database
            event_id = None
            persisted_anomalies = []

            async with async_session_factory() as session:
                event_record = AccessEvent(
                    timestamp=datetime.now(timezone.utc),
                    username=event_data.get("username", "anonymous"),
                    user_role=event_data.get("user_role", "analyst"),
                    resource_key=event_data.get("resource_key", "UNKNOWN"),
                    resource_type=event_data.get("resource_type", "GENERIC"),
                    sensitivity_level=event_data.get("sensitivity_level", "INTERNAL"),
                    action=event_data.get("action", "READ"),
                    client_ip=event_data.get("client_ip", "127.0.0.1"),
                    status_code=event_data.get("status_code", 200),
                    latency_ms=event_data.get("latency_ms", 0.0),
                    is_synthetic=event_data.get("is_synthetic", False),
                )
                session.add(event_record)
                await session.flush()  # obtain event_record.id
                event_id = event_record.id

                for anom in flagged:
                    anomaly_record = Anomaly(
                        timestamp=datetime.now(timezone.utc),
                        event_id=event_id,
                        username=event_data.get("username", "anonymous"),
                        resource_key=event_data.get("resource_key", "UNKNOWN"),
                        anomaly_type=anom["anomaly_type"],
                        severity=anom["severity"],
                        score=anom["score"],
                        explanation=anom["explanation"],
                        details_json=json.dumps(anom.get("details", {})),
                        is_resolved=False,
                    )
                    session.add(anomaly_record)
                    await session.flush()
                    persisted_anomalies.append(anomaly_record.to_dict())

                await session.commit()

            # 3. Broadcast to all active WebSocket clients on dashboard
            # Broadcast the access event
            event_summary = {
                "id": event_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "username": event_data.get("username"),
                "resource_key": event_data.get("resource_key"),
                "resource_type": event_data.get("resource_type"),
                "sensitivity_level": event_data.get("sensitivity_level"),
                "action": event_data.get("action"),
                "client_ip": event_data.get("client_ip"),
                "status_code": event_data.get("status_code"),
                "is_synthetic": event_data.get("is_synthetic", False),
                "has_anomaly": len(persisted_anomalies) > 0,
            }
            await ws_manager.broadcast({
                "type": "ACCESS_EVENT",
                "data": event_summary,
            })

            # Broadcast each flagged anomaly with high priority
            for anom_dict in persisted_anomalies:
                await ws_manager.broadcast({
                    "type": "ANOMALY_ALERT",
                    "data": anom_dict,
                })

        except asyncio.CancelledError:
            logger.info("Event processing worker received cancellation.")
            break
        except Exception as e:
            logger.error(f"Unexpected error in event worker: {e}", exc_info=True)
            await asyncio.sleep(0.5)

    logger.info("Real-time streaming event worker exited cleanly.")


def start_event_worker():
    """Start the background processing task."""
    global _worker_task, _is_running
    if not _is_running:
        _is_running = True
        _worker_task = asyncio.create_task(event_processing_worker())


def stop_event_worker():
    """Signal worker to terminate and await cancellation."""
    global _worker_task, _is_running
    _is_running = False
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()
