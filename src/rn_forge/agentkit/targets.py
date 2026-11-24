"""Resolve where an agentkit run reads from and writes to."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.runtime.subprocess import Process

from rn_forge.agentkit.sources import Scope, repo_overlay_path, user_overlay_path


class Agent(StrEnum):
    """The agents agentkit renders configuration for."""

    CLAUDE = "claude"
    CODEX = "codex"


@dataclass(frozen=True, slots=True)
class Target:
    """The root an apply writes into and the work dir that holds its state."""

    scope: Scope
    root: Path
    work_dir: Path
    rnf_home: Path

    @property
    def state_path(self) -> Path:
        """The state file."""
        return self.work_dir / "state.json"

    @property
    def backup_dir(self) -> Path:
        """Where overwritten files are backed up."""
        return self.work_dir / "backups"

    @property
    def staging_dir(self) -> Path:
        """Where content is staged before the swap."""
        return self.work_dir / ".staging"

    @property
    def user_overlay(self) -> Path:
        """The user overlay file."""
        return user_overlay_path(self.rnf_home)

    @property
    def repo_overlay(self) -> Path:
        """The repository overlay file."""
        return repo_overlay_path(self.root)


def resolve_target(
    scope: Scope, *, repo: Path | None, cwd: Path, home: Path, rnf_home: Path
) -> Target:
    """Resolve the target for *scope*.

    Raises:
        AppException: Repository scope, no *repo*, and *cwd* is not in a git
            repository.
    """
    if scope is Scope.MACHINE:
        return Target(scope, home, rnf_home / "share" / "agentkit", rnf_home)
    if repo is not None:
        root = repo
    else:
        result = Process.execute(
            "git",
            "git",
            "rev-parse",
            "--show-toplevel",
            cwd=cwd,
            fail_on_error=False,
        )
        top = (result.stdout or "").strip()
        if not result.succeeded or not top:
            raise AppException("not inside a git repository: {}", cwd)
        root = Path(top).resolve()
    return Target(scope, root, root / ".rn-forge" / "agentkit", rnf_home)
