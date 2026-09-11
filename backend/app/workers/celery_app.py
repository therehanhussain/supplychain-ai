"""Celery Worker Application Instance.

Configures asynchronous task execution using Redis as the message broker
and result backend. Concurrency is strictly driven by environment configuration.
"""

from celery import Celery
from backend.app.core.config import settings

celery_app = Celery(
    "supplychain_workers",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["backend.app.workers.tasks"],
)

# Production Celery Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=86400,  # 24 hours
)
