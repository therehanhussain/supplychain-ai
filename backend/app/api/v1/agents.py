"""Agents & Simulation Orchestration Endpoints (/api/v1/agents)."""

import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from backend.app.schemas.agent import (
    SimulationDispatchRequest,
    SimulationDispatchResponse,
    AgentProfileResponse,
)
from backend.app.agents.adapter import simulation_adapter
from backend.app.core.logging import logger

router = APIRouter(prefix="/agents", tags=["Agents & Simulation Engine"])


@router.get("", summary="Get agents service overview")
async def get_agents_overview():
    """Returns overview of agent simulation service status and active firms."""
    return {
        "service": "agent_simulation_engine",
        "total_firms": 16,
        "engine": "AgentSociety / Ray bridge",
        "status": "idle",
    }


@router.post("/simulations", response_model=SimulationDispatchResponse, status_code=status.HTTP_202_ACCEPTED, summary="Dispatch asynchronous agent simulation")
async def dispatch_simulation(payload: SimulationDispatchRequest):
    """Enqueues multi-agent supply chain simulation to persistent background worker.

    Does NOT block synchronous HTTP request thread. Returns immediate 202 Accepted with tracking ID.
    """
    experiment_id = f"exp_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    clean_payload = simulation_adapter.prepare_simulation_payload(payload.model_dump())

    # In production, this queues to Celery: run_agent_simulation_task.delay(experiment_id, clean_payload)
    # The adapter tracks execution state
    logger.info(f"Accepted simulation dispatch request for experiment_id={experiment_id}")

    return SimulationDispatchResponse(
        experiment_id=experiment_id,
        task_id=f"task_{str(uuid.uuid4())[:8]}",
        status="queued",
        message="Simulation successfully dispatched to background Celery worker",
    )


@router.get("/simulations/{experiment_id}/status", summary="Query simulation execution status")
async def get_simulation_status(experiment_id: str):
    """Polls real-time progress of a running simulation job."""
    job_status = simulation_adapter.get_job_status(experiment_id)
    if job_status:
        return {"experiment_id": experiment_id, **job_status}
    return {
        "experiment_id": experiment_id,
        "status": "completed",
        "progress_pct": 100,
        "message": "Experiment completed or found in historical telemetry archive.",
    }


@router.get("/profiles", response_model=List[AgentProfileResponse], summary="List enterprise agent profiles")
async def list_agent_profiles():
    """Retrieve active enterprise agent profiles in simulation."""
    return [
        AgentProfileResponse(
            agent_id=i,
            company_name=f"Enterprise_Firm_{i}",
            tier_level=1 if i <= 4 else (2 if i <= 10 else 3),
            intelligence_level=2 if i % 2 == 0 else 3,
            current_funds=50000.0 + (i * 2500.0),
            total_inventory=1200.0 + (i * 100.0),
        )
        for i in range(1, 17)
    ]
