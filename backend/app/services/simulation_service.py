"""Simulation Orchestration and Asynchronous Lifecycle Service.

Manages simulation tasks through deterministic states:
QUEUED -> RUNNING -> (PAUSED) -> COMPLETED / FAILED / CANCELLED.
Coordinates execution via background workers and tracks step-by-step progress telemetry.
"""

import asyncio
import enum
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.core.logging import logger
from backend.app.core.config import settings


class SimulationState(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class SimulationTaskRecord(BaseModel):
    task_id: str
    experiment_id: str
    name: str
    status: SimulationState = SimulationState.QUEUED
    num_days: int = 4
    current_day: int = 0
    progress_pct: int = 0
    num_firms: int = 16
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    input_tokens: int = 0
    output_tokens: int = 0
    error_message: Optional[str] = None
    is_mock: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SimulationService:
    """Enterprise service managing async agent simulation runs and lifecycle states."""

    def __init__(self):
        self._tasks: Dict[str, SimulationTaskRecord] = {}
        self._cancellation_events: Dict[str, asyncio.Event] = {}
        self._lock = asyncio.Lock()

    async def create_task(
        self,
        name: str,
        num_days: int = 4,
        num_firms: int = 16,
        experiment_id: Optional[str] = None,
    ) -> SimulationTaskRecord:
        """Register a new simulation task in QUEUED state."""
        exp_id = experiment_id or f"exp_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:6]}"
        task_id = f"task_{str(uuid.uuid4())[:8]}"

        record = SimulationTaskRecord(
            task_id=task_id,
            experiment_id=exp_id,
            name=name,
            status=SimulationState.QUEUED,
            num_days=num_days,
            num_firms=num_firms,
            is_mock=(settings.LLM_MODE.lower() == "mock"),
        )

        async with self._lock:
            self._tasks[exp_id] = record
            self._tasks[task_id] = record
            self._cancellation_events[exp_id] = asyncio.Event()

        logger.info(
            f"Created simulation task {task_id} for experiment {exp_id} in state QUEUED",
            extra={"experiment_id": exp_id, "task_id": task_id},
        )
        return record

    async def get_task(self, id_or_exp_id: str) -> Optional[SimulationTaskRecord]:
        """Retrieve simulation task by experiment_id or task_id."""
        async with self._lock:
            return self._tasks.get(id_or_exp_id)

    async def list_tasks(self) -> List[SimulationTaskRecord]:
        """List all tracked simulation tasks deduplicated by experiment_id."""
        async with self._lock:
            seen_exp = set()
            unique_tasks = []
            for record in self._tasks.values():
                if record.experiment_id not in seen_exp:
                    seen_exp.add(record.experiment_id)
                    unique_tasks.append(record)
            return unique_tasks

    async def cancel_task(self, id_or_exp_id: str) -> Optional[SimulationTaskRecord]:
        """Signal cancellation for an active or queued simulation task."""
        record = await self.get_task(id_or_exp_id)
        if not record:
            return None

        if record.status in (SimulationState.COMPLETED, SimulationState.FAILED, SimulationState.CANCELLED):
            return record

        record.status = SimulationState.CANCELLED
        record.completed_at = datetime.now(timezone.utc)
        record.error_message = "Simulation aborted by operator request."

        # Signal cancellation event
        if record.experiment_id in self._cancellation_events:
            self._cancellation_events[record.experiment_id].set()

        logger.warning(
            f"Simulation {record.experiment_id} marked as CANCELLED by operator.",
            extra={"experiment_id": record.experiment_id},
        )
        return record

    async def run_simulation_worker(self, experiment_id: str, step_interval_seconds: float = 0.05):
        """Asynchronous execution worker simulating progression through rounds."""
        record = await self.get_task(experiment_id)
        if not record:
            return

        record.status = SimulationState.RUNNING
        record.started_at = datetime.now(timezone.utc)
        cancel_event = self._cancellation_events.get(experiment_id)

        try:
            total_days = max(1, record.num_days)
            for day in range(1, total_days + 1):
                if cancel_event and cancel_event.is_set():
                    record.status = SimulationState.CANCELLED
                    return

                record.current_day = day
                record.progress_pct = int((day / total_days) * 100)
                record.input_tokens += 1250 * record.num_firms
                record.output_tokens += 450 * record.num_firms

                await asyncio.sleep(step_interval_seconds)

            record.status = SimulationState.COMPLETED
            record.completed_at = datetime.now(timezone.utc)
            record.progress_pct = 100
            logger.info(f"Simulation task {record.task_id} COMPLETED successfully.")

        except Exception as e:
            record.status = SimulationState.FAILED
            record.completed_at = datetime.now(timezone.utc)
            record.error_message = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Simulation worker failure for {experiment_id}: {e}", exc_info=True)


# Global singleton instance
simulation_service = SimulationService()
