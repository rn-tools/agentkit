"""Detect a v0 installation and archive its state before cutover."""

import json
import re
from pathlib import Path

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.findings import Finding, Severity
from rn_forge.tooling.install import ToolHome


def _state_path(root: Path) -> Path:
    return root / "share" / "agentkit" / "state.json"


def is_v0_state(path: Path) -> bool:
    """Return whether the file contains a JSON object without a schema version."""
    if not path.is_file():
        return False
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except ValueError, FileNotFoundError:
        return False
    return isinstance(document, dict) and "schema_version" not in document


def check_v0(home: ToolHome) -> list[Finding]:
    """Report the runbook steps for an old install or state file."""
    install = home.root / "agentkit"
    state = _state_path(home.root)
    findings: list[Finding] = []
    if install.is_dir() and any(
        re.fullmatch(r"v\d+\.\d+\.\d+", child.name) and child.is_dir()
        for child in install.iterdir()
    ):
        findings.append(
            Finding(
                "agentkit.v0-install",
                Severity.WARNING,
                f"old agentkit install at {install} (v0 layout): move it aside, "
                "see docs/runbooks/cutover-from-v0.md step 2",
            )
        )
    if is_v0_state(state):
        findings.append(
            Finding(
                "agentkit.v0-state",
                Severity.ERROR,
                f"old-format state file {state}: run agentkit migrate-v0, "
                "see docs/runbooks/cutover-from-v0.md step 4",
            )
        )
    return findings


def migrate_v0(rnf_home: Path) -> Path | None:
    """Archive v0 state and return its new path, or None if there is none.

    Raises:
        AppException: A v0 state file and its archive both exist.
    """
    state = _state_path(rnf_home)
    if not is_v0_state(state):
        return None
    archive = state.with_name("state.v0.json")
    if archive.exists(follow_symlinks=False):
        raise AppException(
            "{} and {} both exist; move {} aside by hand", state, archive, archive
        )
    return state.rename(archive)
