"""The Codex adapter: plain data, filled in by later stories."""

from __future__ import annotations

from rn_forge.agentkit.adapters.spec import Adapter
from rn_forge.agentkit.targets import Agent

ADAPTER = Adapter(Agent.CODEX, {})
