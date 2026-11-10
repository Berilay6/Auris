"""AURIS Celery application — simulation worker (AS5).

References: HLD MK4 (asynchronous job queue), §3.6.2 (concurrency = 1), §3.5.3.

Flow:
    auris-backend  --(task)-->  auris-broker ("simulation" queue)  -->  auris-worker

Settings are read from environment variables (docker-compose.yml → x-python-env):
    CELERY_BROKER_URL      redis://auris-broker:6379/0
    CELERY_RESULT_BACKEND  redis://auris-broker:6379/1

The worker is started with (same as the compose command):
    celery --app=auris.simulation.celery_app worker --concurrency=1 \
        --prefetch-multiplier=1 --queues=simulation
"""

from __future__ import annotations

import os

from celery import Celery
from kombu import Queue

SIMULATION_QUEUE = "simulation"

# TODO(SCRUM-10): read these two values from core/config.py once it is ready.
BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

app = Celery(
    "auris",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["auris.simulation.tasks"],
)

app.conf.update(
    # --- Queue ----------------------------------------------------------------
    task_queues=(Queue(SIMULATION_QUEUE),),
    task_default_queue=SIMULATION_QUEUE,
    task_create_missing_queues=False,  # a misspelled queue name must not silently create a new queue
    # --- Concurrency (HLD §3.6.2) --------------------------------------------
    # SUMO is CPU- and memory-heavy; only one simulation runs at a time.
    # Prefetch 1: the worker does not reserve the next job while it is busy.
    worker_concurrency=1,
    worker_prefetch_multiplier=1,
    # --- Serialization --------------------------------------------------------
    # JSON only
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # --- Time -----------------------------------------------------------------
    enable_utc=True,
    timezone="UTC",
    # --- Connection -----------------------------------------------------------
    broker_connection_retry_on_startup=True,
)
