"""The seam between agentkit's merged sources and the artifacts it writes."""

from __future__ import annotations

from collections.abc import Sequence

from rn_forge.commons.generation import Artifact
from rn_forge.commons.lang.collections import MergeResult

from rn_forge.agentkit.targets import Agent, Target


def render(
    target: Target, agents: Sequence[Agent], sources: MergeResult
) -> list[Artifact]:
    """Render the artifacts for *agents*; F1.4's adapters fill this in."""
    return []
