# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""ACAP middleware for caller and callee agents.

These modules are intentionally thin. They wrap standard HTTP interactions
with the consent handshake and the per-action adherence recording described
in the Anumati paper (§4). Both modules are framework-agnostic and do not
require modification of the A2A or MCP core runtimes; they operate at the
boundary between an agent's own logic and the transport layer.
"""

from acap.middleware.caller import ACAPCaller, ClaimParser
from acap.middleware.callee import ACAPCallee, build_fastapi_router

__all__ = [
    "ACAPCaller",
    "ACAPCallee",
    "ClaimParser",
    "build_fastapi_router",
]
