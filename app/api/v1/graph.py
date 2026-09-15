"""Graph topology API endpoint for frontend visualization."""
from fastapi import APIRouter, Depends
from app.api.deps import require_analyst_or_admin
from app.detection.engine import detection_engine
from app.db.models import User

router = APIRouter(prefix="/graph", tags=["Graph Topology"])


@router.get("/topology")
async def get_graph_topology(current_user: User = Depends(require_analyst_or_admin)):
    """Return the current NetworkX bipartite access graph topology."""
    return detection_engine.get_topology()
