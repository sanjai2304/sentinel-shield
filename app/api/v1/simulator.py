"""Simulator and attack scenario trigger endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.api.deps import require_analyst_or_admin
from app.simulator.traffic_generator import simulator
from app.simulator.attack_scenarios import (
    run_exfiltration_spike,
    run_novelty_attack,
    run_fanout_sweep,
)
from app.db.models import User

router = APIRouter(prefix="/simulator", tags=["Traffic Simulator & Attacks"])


class SpeedRequest(BaseModel):
    multiplier: float = 1.0


@router.get("/status")
async def get_simulator_status(current_user: User = Depends(require_analyst_or_admin)):
    """Check whether background synthetic generator is running."""
    return simulator.get_status()


@router.post("/start")
async def start_simulator(current_user: User = Depends(require_analyst_or_admin)):
    """Resume or start continuous synthetic background traffic."""
    simulator.start()
    return {"status": "started", **simulator.get_status()}


@router.post("/stop")
async def stop_simulator(current_user: User = Depends(require_analyst_or_admin)):
    """Pause synthetic background traffic."""
    simulator.stop()
    return {"status": "stopped", **simulator.get_status()}


@router.post("/speed")
async def change_speed(body: SpeedRequest, current_user: User = Depends(require_analyst_or_admin)):
    """Adjust synthetic generation frequency."""
    simulator.set_speed(body.multiplier)
    return {"status": "speed_updated", **simulator.get_status()}


@router.post("/attack/{scenario}")
async def trigger_attack_scenario(scenario: str, current_user: User = Depends(require_analyst_or_admin)):
    """Trigger a pre-programmed attack scenario to observe real-time anomaly detection.

    Scenarios:
    - `exfiltration`: High-velocity burst to PII vault (Z-Score statistical detector)
    - `novelty`: Unauthorized leap into Top Secret HSM key vault (NetworkX novelty detector)
    - `fanout`: Rapid sweep across 6+ sensitive databases (NetworkX horizontal fan-out detector)
    """
    scenario = scenario.lower()
    if scenario in ("exfiltration", "exfiltration_spike", "burst"):
        result = await run_exfiltration_spike()
    elif scenario in ("novelty", "novelty_attack", "privilege_leap"):
        result = await run_novelty_attack()
    elif scenario in ("fanout", "fanout_sweep", "sweep"):
        result = await run_fanout_sweep()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown attack scenario '{scenario}'. Available: 'exfiltration', 'novelty', 'fanout'."
        )

    return result
