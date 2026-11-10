"""Simulation tasks (AS5).

Sprint 1: only ``ping`` exists, as a connectivity test.
The real simulation task (duarouter + sumo) will be added here in Sprint 3.
"""

from __future__ import annotations

import socket
from datetime import datetime, timezone

from auris.simulation.celery_app import app


@app.task(name="auris.simulation.ping")
def ping() -> dict[str, str]:
    """Verify the queue → worker → result backend chain end to end.

    Does no real work. If ``ping.delay().get(timeout=10)`` returns a dict,
    the broker connection, the ``simulation`` queue and the result backend
    are all working.
    """
    return {
        "status": "pong",
        "worker": socket.gethostname(),
        "at": datetime.now(timezone.utc).isoformat(),
    }
