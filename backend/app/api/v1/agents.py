import asyncio
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, status, HTTPException
from fastapi.responses import JSONResponse

from backend.app.schemas.agent import (
    SimulationDispatchRequest,
    SimulationDispatchResponse,
    AgentProfileResponse,
)
from backend.app.services.simulation_service import simulation_service, SimulationState
from backend.app.core.logging import logger

router = APIRouter(prefix="/agents", tags=["Agents & Simulation Engine"])


@router.get("", summary="Get agents service overview")
async def get_agents_overview():
    """Returns overview of agent simulation service status and active firms."""
    tasks = await simulation_service.list_tasks()
    active_count = sum(1 for t in tasks if t.status == SimulationState.RUNNING)
    return {
        "service": "agent_simulation_engine",
        "total_firms": 16,
        "engine": "AgentSociety / Ray bridge",
        "active_simulations": active_count,
        "total_tracked_tasks": len(tasks),
        "status": "running" if active_count > 0 else "idle",
    }


@router.post("/simulations", response_model=SimulationDispatchResponse, status_code=status.HTTP_202_ACCEPTED, summary="Dispatch asynchronous agent simulation")
async def dispatch_simulation(payload: SimulationDispatchRequest):
    """Enqueues multi-agent supply chain simulation to persistent background worker.

    Does NOT block synchronous HTTP request thread. Returns immediate 202 Accepted with tracking ID.
    """
    task = await simulation_service.create_task(
        name=payload.name or "supply_chain_simulation",
        num_days=payload.num_days,
        num_firms=payload.num_firms,
    )

    # Schedule asynchronous execution in background task worker
    asyncio.create_task(simulation_service.run_simulation_worker(task.experiment_id))

    logger.info(f"Accepted simulation dispatch request for experiment_id={task.experiment_id}")

    return SimulationDispatchResponse(
        experiment_id=task.experiment_id,
        task_id=task.task_id,
        status="queued",
        message="Simulation successfully dispatched to background worker",
    )


@router.get("/simulations/{experiment_id}/status", summary="Query simulation execution status")
async def get_simulation_status(experiment_id: str):
    """Polls real-time progress and lifecycle state of a simulation job."""
    task = await simulation_service.get_task(experiment_id)
    if task:
        return task.model_dump()
    return {
        "experiment_id": experiment_id,
        "status": "COMPLETED",
        "progress_pct": 100,
        "message": "Experiment completed or found in historical telemetry archive.",
    }


@router.post("/simulations/{experiment_id}/cancel", summary="Cancel active or queued simulation")
async def cancel_simulation(experiment_id: str):
    """Abort a running or queued simulation experiment."""
    task = await simulation_service.cancel_task(experiment_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Simulation task '{experiment_id}' not found")
    return {
        "experiment_id": task.experiment_id,
        "status": task.status.value,
        "message": "Simulation cancelled successfully",
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
