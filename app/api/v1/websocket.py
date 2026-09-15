"""WebSocket endpoint streaming live anomalies, access events, and topology updates."""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select, desc, func
from app.streaming.connection_manager import ws_manager
from app.db.session import async_session_factory
from app.db.models import Anomaly, AccessEvent
from app.detection.engine import detection_engine
from app.simulator.traffic_generator import simulator

logger = logging.getLogger("sentinel.ws_route")
router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/dashboard")
async def websocket_dashboard_endpoint(websocket: WebSocket):
    """WebSocket stream powering the live Security Operations Center (SOC) dashboard."""
    await ws_manager.connect(websocket)
    try:
        # 1. Send initial state snapshot and cumulative metrics on connection
        async with async_session_factory() as session:
            # Cumulative total event & anomaly counts for realistic rate calculation
            tot_events_q = await session.execute(select(func.count(AccessEvent.id)))
            total_events_count = tot_events_q.scalar() or 0

            tot_anoms_q = await session.execute(select(func.count(Anomaly.id)))
            total_anomalies_count = tot_anoms_q.scalar() or 0

            # Fetch last 15 anomalies
            anom_res = await session.execute(
                select(Anomaly).order_by(desc(Anomaly.timestamp)).limit(15)
            )
            recent_anomalies = [a.to_dict() for a in anom_res.scalars().all()]

            # Fetch last 20 access events
            event_res = await session.execute(
                select(AccessEvent).order_by(desc(AccessEvent.timestamp)).limit(20)
            )
            recent_events = [e.to_dict() for e in event_res.scalars().all()]

        # Initial handshake message
        await websocket.send_json({
            "type": "INITIAL_STATE",
            "data": {
                "cumulative": {
                    "total_events": total_events_count,
                    "total_anomalies": total_anomalies_count,
                },
                "recent_anomalies": recent_anomalies,
                "recent_events": recent_events,
                "topology": detection_engine.get_topology(),
                "simulator_status": simulator.get_status(),
            },
        })

        # Keep connection open and handle incoming client requests if any
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            elif data == "refresh_topology":
                await websocket.send_json({
                    "type": "TOPOLOGY_UPDATE",
                    "data": detection_engine.get_topology(),
                })

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket client error: {e}")
        ws_manager.disconnect(websocket)
