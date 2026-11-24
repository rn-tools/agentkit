"""The commands this repo's CLI exposes.

A command function is all a repository writes. The application around it —
the root callback, the standard `--log-level`/`--json` flags, the
error-to-exit-code mapping — is built from the `[cli]` table in
`.rn-forge/kiln/config.toml`.
"""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from rn_forge.cli import DryRunOption, YesOption
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.findings import Severity
from rn_forge.commons.generation import Change
from rn_forge.commons.runtime.console import OutputMode, console
from rn_forge.tooling.install import rnf_home

from rn_forge.agentkit import cutover, operations
from rn_forge.agentkit import review as reviewing
from rn_forge.agentkit.findings import scope_findings
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


def plan(
    scope: Scope = Scope.MACHINE,
    repo: Path | None = None,
    agent: list[Agent] | None = None,
) -> None:
    """Show the per-artifact plan and the scope's findings."""
    target = _target(scope, repo)
    agents = _agents(agent)
    findings = scope_findings(target, agents)
    rows: list[dict[str, str]] = []
    if not any(f.code == "agentkit.overlay-invalid" for f in findings):
        rows = _rows(operations.build_plan(target, agents)[0].changes)
    if console.mode is OutputMode.JSON:
        console.emit({"changes": rows, "findings": [f.as_dict() for f in findings]})
    else:
        for row in rows:
            console.print(
                "{} {} {}", row["action"], row["kind"], row["path"], markup=False
            )
        for finding in findings:
            console.print(
                "{} {} {}",
                finding.severity,
                finding.code,
                finding.message,
                markup=False,
            )
    errors = sum(f.severity is Severity.ERROR for f in findings)
    if errors:
        raise AppException("{} error finding(s)", errors)


def review(scope: Scope = Scope.MACHINE, repo: Path | None = None) -> None:
    """Suggest improvements to the scope's instruction files; never writes."""
    suggestions = reviewing.review(_target(scope, repo))
    if console.mode is OutputMode.JSON:
        console.emit([asdict(suggestion) for suggestion in suggestions])
    elif not suggestions:
        console.print("no suggestions", markup=False)
    elif console.mode is not OutputMode.QUIET:
        for suggestion in suggestions:
            console.rich.print(
                f"{suggestion.path}:{suggestion.line}: {suggestion.code} {suggestion.message}",
                markup=False,
                emoji=False,
                soft_wrap=True,
            )


def remove(
    scope: Scope = Scope.MACHINE,
    repo: Path | None = None,
    yes: YesOption = False,
) -> None:
    """Take back everything agentkit recorded in the scope."""
    target = _target(scope, repo)
    result, left = operations.run_remove(target)
    if console.mode is OutputMode.JSON:
        console.emit({"changes": _rows(result.changes), "left": [c.path for c in left]})
    else:
        for change in result.changes:
            console.print("{} {}", change.action, change.path, markup=False)
        for change in left:
            console.print("left in place (drift): {}", change.path, markup=False)
    if scope is Scope.MACHINE and (
        yes
        or console.confirm(
            f"Delete {target.work_dir}, including its backups and your overlay?",
            default=False,
        )
    ):
        shutil.rmtree(target.work_dir)


def migrate_v0() -> None:
    """Rename a v0 state file to state.v0.json; never deletes it."""
    archive = cutover.migrate_v0(rnf_home())
    if console.mode is OutputMode.JSON:
        console.emit({"archived": str(archive) if archive is not None else None})
    elif archive is None:
        console.print("nothing to migrate")
    else:
        console.print(
            "renamed {} -> {}", archive.with_name("state.json"), archive, markup=False
        )
