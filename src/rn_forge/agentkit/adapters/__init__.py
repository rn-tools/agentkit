"""The seam between agentkit's merged sources and the artifacts it writes."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from importlib.resources import files
from pathlib import Path
from typing import cast

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.generation import Artifact
from rn_forge.commons.lang.collections import MergeResult
from rn_forge.commons.text.templates import TemplateEngine

from rn_forge.agentkit.adapters import claude, codex, hooks
from rn_forge.agentkit.adapters.spec import Adapter, ArtifactSpec, Base
from rn_forge.agentkit.sources import Scope, SourceError
from rn_forge.agentkit.targets import Agent, Target

__all__ = [
    "ADAPTERS",
    "ASSETS",
    "COMMON",
    "Adapter",
    "ArtifactSpec",
    "Base",
    "executable_paths",
    "owned_paths",
    "render",
]

ASSETS = Path(str(files("rn_forge.agentkit").joinpath("assets")))
ADAPTERS: dict[Agent, Adapter] = {
    Agent.CLAUDE: claude.ADAPTER,
    Agent.CODEX: codex.ADAPTER,
}


COMMON: dict[Scope, tuple[ArtifactSpec, ...]] = {Scope.MACHINE: hooks.COMMON}


def _specs(scope: Scope, agents: Iterable[Agent]) -> list[ArtifactSpec]:
    return [spec for agent in agents for spec in ADAPTERS[agent].specs.get(scope, ())]


def _destination(target: Target, spec: ArtifactSpec) -> str:
    if spec.base is Base.ROOT:
        return spec.path
    if not target.work_dir.is_relative_to(target.root):
        raise AppException(
            "{} is outside {}: agentkit installs its hook scripts there, "
            "so RNF_HOME must be under HOME",
            target.work_dir,
            target.root,
        )
    return (target.work_dir.relative_to(target.root) / spec.path).as_posix()


def _emit(
    target: Target, spec: ArtifactSpec, context: Mapping[str, object]
) -> Artifact:
    if spec.template:
        content = TemplateEngine.cached(directory=str(ASSETS)).render(
            spec.source, context
        )
    else:
        content = (ASSETS / spec.source).read_text(encoding="utf-8")
    return Artifact(_destination(target, spec), spec.kind, content, block=spec.block)


def render(
    target: Target, agents: Sequence[Agent], sources: MergeResult
) -> list[Artifact]:
    """Render the artifacts the adapters of *agents* declare for the target scope.

    Raises:
        SourceError: An agent's ``skills.disabled`` is not a list of strings.
    """
    artifacts: list[Artifact] = []
    for agent in agents:
        context: dict[str, object] = {
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
        artifacts.extend(
            _emit(target, spec, context)
            for spec in _specs(target.scope, [agent])
            if spec.skill not in cast("list[str]", disabled)
        )
    if agents:
        common: dict[str, object] = {
            "agent": "_common",
            "scope": target.scope.value,
            "config": {},
        }
        artifacts.extend(
            _emit(target, spec, common) for spec in COMMON.get(target.scope, ())
        )
    return artifacts


def owned_paths(target: Target, agents: Iterable[Agent]) -> frozenset[str]:
    """The paths the adapters of *agents* declare for the target, without rendering."""
    return frozenset(_destination(target, s) for s in _specs(target.scope, agents))


def executable_paths(target: Target, agents: Iterable[Agent]) -> frozenset[str]:
    """The declared paths of *agents* that must be mode 0755 after apply."""
    specs = [*_specs(target.scope, agents), *COMMON.get(target.scope, ())]
    return frozenset(_destination(target, s) for s in specs if s.executable)
