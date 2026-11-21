"""The seam between agentkit's merged sources and the artifacts it writes."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from importlib.resources import files
from pathlib import Path
from typing import cast

from rn_forge.commons.generation import Artifact
from rn_forge.commons.lang.collections import MergeResult
from rn_forge.commons.text.templates import TemplateEngine

from rn_forge.agentkit.adapters import claude, codex
from rn_forge.agentkit.adapters.spec import Adapter, ArtifactSpec
from rn_forge.agentkit.sources import Scope, SourceError
from rn_forge.agentkit.targets import Agent, Target

__all__ = [
    "ADAPTERS",
    "ASSETS",
    "Adapter",
    "ArtifactSpec",
    "executable_paths",
    "owned_paths",
    "render",
]

ASSETS = Path(str(files("rn_forge.agentkit").joinpath("assets")))
ADAPTERS: dict[Agent, Adapter] = {
    Agent.CLAUDE: claude.ADAPTER,
    Agent.CODEX: codex.ADAPTER,
}


def _specs(scope: Scope, agents: Iterable[Agent]) -> list[ArtifactSpec]:
    return [spec for agent in agents for spec in ADAPTERS[agent].specs.get(scope, ())]


def render(
    target: Target, agents: Sequence[Agent], sources: MergeResult
) -> list[Artifact]:
    """Render the artifacts the adapters of *agents* declare for the target scope.

    Raises:
        SourceError: An agent's ``skills.disabled`` is not a list of strings.
    """
    artifacts: list[Artifact] = []
    for agent in agents:
        context = {
            "agent": agent.value,
            "scope": target.scope.value,
            "config": sources.config.get(agent.value, {}),
        }
        disabled: object = (
            sources.config.get(agent.value, {}).get("skills", {}).get("disabled", [])
        )
        if not isinstance(disabled, list) or not all(
            isinstance(item, str) for item in cast("list[object]", disabled)
        ):
            raise SourceError(
                "[{}] skills.disabled: expected a list of skill names, got {!r}",
                agent.value,
                disabled,
            )
        for spec in _specs(target.scope, [agent]):
            if spec.skill in cast("list[str]", disabled):
                continue
            if spec.template:
                content = TemplateEngine.cached(directory=str(ASSETS)).render(
                    spec.source, context
                )
            else:
                content = (ASSETS / spec.source).read_text(encoding="utf-8")
            artifacts.append(Artifact(spec.path, spec.kind, content, block=spec.block))
    return artifacts


def owned_paths(scope: Scope, agents: Iterable[Agent]) -> frozenset[str]:
    """The paths the adapters of *agents* declare for *scope*, without rendering."""
    return frozenset(spec.path for spec in _specs(scope, agents))


def executable_paths(scope: Scope, agents: Iterable[Agent]) -> frozenset[str]:
    """The declared paths of *agents* that must be mode 0755 after apply."""
    return frozenset(spec.path for spec in _specs(scope, agents) if spec.executable)
