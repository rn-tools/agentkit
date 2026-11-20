"""The commands this repo's CLI exposes.

A command function is all a repository writes. The application around it —
the root callback, the standard `--log-level`/`--json` flags, the
error-to-exit-code mapping — is built from the `[cli]` table in
`.rn-forge/kiln/config.toml`.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from rn_forge.cli import DryRunOption
from rn_forge.commons.generation import Change
from rn_forge.commons.runtime.console import OutputMode, console
from rn_forge.tooling.install import rnf_home

from rn_forge.agentkit import operations
from rn_forge.agentkit.sources import Scope
from rn_forge.agentkit.targets import Agent, Target, resolve_target


def _target(scope: Scope, repo: Path | None) -> Target:
    return resolve_target(
        scope, repo=repo, cwd=Path.cwd(), home=Path.home(), rnf_home=rnf_home()
    )


def _agents(agent: Sequence[Agent] | None) -> list[Agent]:
    return list(agent) if agent else list(Agent)


def _rows(changes: Sequence[Change]) -> list[dict[str, str]]:
    return [
        {"path": c.path, "kind": str(c.kind), "action": str(c.action)} for c in changes
    ]


def apply(
    scope: Scope = Scope.MACHINE,
    repo: Path | None = None,
    agent: list[Agent] | None = None,
    force: list[str] | None = None,
    dry_run: DryRunOption = False,
) -> None:
    """Write agent configuration for the scope, transactionally."""
    result = operations.run_apply(
        _target(scope, repo),
        _agents(agent),
        force=force or (),
        dry_run=dry_run,
    )
    if console.mode is OutputMode.JSON:
        console.emit(_rows(result.changes))
        return
    for change in result.changes:
        console.print("{} {}", change.action, change.path, markup=False)


def diff(
    scope: Scope = Scope.MACHINE,
    repo: Path | None = None,
    agent: list[Agent] | None = None,
) -> None:
    """Show what apply would change, writing nothing."""
    planned, diffs = operations.run_diff(_target(scope, repo), _agents(agent))
    if console.mode is OutputMode.JSON:
        console.emit(_rows(planned.changes))
        return
    for text in diffs:
        console.print(text, markup=False)
