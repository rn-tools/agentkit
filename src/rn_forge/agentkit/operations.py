"""Plan, apply and diff agentkit artifacts for a target."""

from __future__ import annotations

from collections.abc import Sequence

from rn_forge.commons.fs.state import StateStore
from rn_forge.commons.generation import (
    WRITE_ACTIONS,
    ApplyResult,
    Change,
    Plan,
    StateEntry,
    apply,
    diff,
    plan,
)

from rn_forge.agentkit import adapters, repository
from rn_forge.agentkit.sources import load_sources
from rn_forge.agentkit.targets import Agent, Target


def _store(target: Target) -> StateStore[StateEntry]:
    return StateStore(target.state_path, entry_type=StateEntry)


def build_plan(
    target: Target, agents: Sequence[Agent], *, force: Sequence[str] = ()
) -> tuple[Plan, dict[str, StateEntry]]:
    """Render for *agents* and classify against the target's state."""
    sources = load_sources(
        target.scope,
        user_overlay=target.user_overlay,
        repo_overlay=target.repo_overlay,
    )
    artifacts = [
        *adapters.render(target, agents, sources),
        *repository.render(target, sources),
    ]
    entries = _store(target).load()
    return plan(target.root, artifacts, entries, force=force), entries


def run_apply(
    target: Target,
    agents: Sequence[Agent],
    *,
    force: Sequence[str] = (),
    dry_run: bool = False,
) -> ApplyResult:
    """Plan, then apply transactionally; blocked plans raise."""
    planned, entries = build_plan(target, agents, force=force)
    return apply(
        target.root,
        planned,
        _store(target),
        staging_dir=target.staging_dir,
        backup_dir=target.backup_dir,
        entries=entries,
        dry_run=dry_run,
    )


def run_remove(target: Target) -> tuple[ApplyResult, list[Change]]:
    """Take back everything recorded; hand-edited paths are left and returned."""
    entries = _store(target).load()
    planned = plan(target.root, [], entries)
    left = [change for change in planned.changes if change.is_blocking]
    rest = Plan(tuple(change for change in planned.changes if not change.is_blocking))
    result = apply(
        target.root,
        rest,
        _store(target),
        staging_dir=target.staging_dir,
        backup_dir=target.backup_dir,
        entries=entries,
    )
    return result, left


def run_diff(target: Target, agents: Sequence[Agent]) -> tuple[Plan, list[str]]:
    """Return the plan and the non-empty diffs of its write changes."""
    planned, _ = build_plan(target, agents)
    diffs = [
        text
        for change in planned.changes
        if change.action in WRITE_ACTIONS and (text := diff(target.root, change))
    ]
    return planned, diffs
