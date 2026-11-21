"""The Codex adapter: its machine-scope specs, one module per feature."""

from __future__ import annotations

from rn_forge.agentkit.adapters import hooks, instructions, skills
from rn_forge.agentkit.adapters.spec import Adapter
from rn_forge.agentkit.sources import Scope
from rn_forge.agentkit.targets import Agent

ADAPTER = Adapter(
    Agent.CODEX,
    {Scope.MACHINE: (*instructions.CODEX, *hooks.CODEX, *skills.CODEX)},
)
