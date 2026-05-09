"""Social media agent — Ara Job entry point.

Deploy:    ara deploy agent/agent.py --cron "*/15 * * * *"
One-off:   ara run agent/agent.py
Logs:      ara logs agent/agent.py
"""

from __future__ import annotations

import ara_sdk as ara

# Importing these modules registers all @ara.tool functions with the runtime.
from tools import approval, state, x_client  # noqa: F401
from prompts import SYSTEM_INSTRUCTIONS


ara.Job(
    "social-agent",
    system_instructions=SYSTEM_INSTRUCTIONS,
)
