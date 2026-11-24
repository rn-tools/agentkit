"""Plan, apply and diff agentkit artifacts for a target."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

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


class _KeepingStore(StateStore[StateEntry]):
    """A store that writes *keep* back alongside the entries it is given."""

    def __init__(self, path: Path, keep: Mapping[str, StateEntry]) -> None:
        super().__init__(path, entry_type=StateEntry)
        self._keep = dict(keep)

    def replace_all(self, entries: Mapping[str, StateEntry]) -> None:
        """Replace the entry set with *entries* plus the kept entries."""
        super().replace_all({**self._keep, **entries})


def make_executable(path: Path) -> None:
    """Set *path* to mode 0755."""
    path.chmod(0o755)


def build_plan(
    target: Target, agents: Sequence[Agent], *, force: Sequence[str] = ()
) -> tuple[Plan, dict[str, StateEntry], dict[str, StateEntry]]:
    """Render for *agents* and classify against the target's state.

    Returns the plan, the entries it planned, and the entries of agents not in
    *agents*, which the plan leaves alone.
    """
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
    others = adapters.owned_paths(target, [a for a in Agent if a not in agents])
    kept = {key: entry for key, entry in entries.items() if entry.path in others}
    rest = {key: entry for key, entry in entries.items() if key not in kept}
    return plan(target.root, artifacts, rest, force=force), rest, kept


def run_apply(
    target: Target,
    agents: Sequence[Agent],
    *,
    force: Sequence[str] = (),
    dry_run: bool = False,
) -> ApplyResult:
    """Plan, then apply transactionally; blocked plans raise."""
    planned, entries, kept = build_plan(target, agents, force=force)
    written = {c.path for c in planned.changes if c.artifact is not None}
    executable = sorted(adapters.executable_paths(target, agents) & written)

    def verify() -> None:
        for path in executable:
            make_executable(target.root / path)

    return apply(
        target.root,
        planned,
        _KeepingStore(target.state_path, kept),
        staging_dir=target.staging_dir,
        backup_dir=target.backup_dir,
        entries=entries,
        verify=verify,
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
    planned, entries, _ = build_plan(target, agents)
    diffs = [
        text
        for change in planned.changes
        if change.action in WRITE_ACTIONS
        and (text := diff(target.root, change, entries=entries))
    ]
    return planned, diffs
