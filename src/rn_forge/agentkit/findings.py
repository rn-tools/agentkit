"""Findings about a scope: missing programs, vanished files, bad overlays.

`plan` prints them for any scope; the lifecycle `doctor` runs the machine
scope's through `check_machine`.
"""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from pathlib import Path

from rn_forge.commons.findings import Finding, Severity
from rn_forge.commons.fs.documents import DocumentError
from rn_forge.commons.fs.state import StateStore
from rn_forge.commons.generation import StateEntry
from rn_forge.tooling.install import ToolHome

from rn_forge.agentkit.instruction_checks import instruction_findings
from rn_forge.agentkit.sources import Scope, SourceError, load_overlay
from rn_forge.agentkit.targets import Agent, Target, resolve_target


def check_jq(home: ToolHome) -> list[Finding]:
    """Report an error when `jq` is not on `PATH`."""
    return _jq_findings()


def _jq_findings() -> list[Finding]:
    if shutil.which("jq"):
        return []
    return [
        Finding(
            "agentkit.jq-missing",
            Severity.ERROR,
            "jq is not on PATH",
        ),
    ]


def _machine_findings(agents: Sequence[Agent]) -> list[Finding]:
    found = [
        Finding(
            "agentkit.agent-missing",
            Severity.WARNING,
            f"{agent} is not on PATH",
        )
        for agent in agents
        if shutil.which(str(agent)) is None
    ]
    found.extend(_jq_findings())
    if shutil.which("gitleaks") is None:
        found.append(
            Finding(
                "agentkit.gitleaks-missing",
                Severity.WARNING,
                "gitleaks is not on PATH",
            )
        )
    return found


def _overlay_paths(target: Target) -> list[Path]:
    paths = [target.user_overlay]
    if target.scope is Scope.REPO:
        paths.append(target.repo_overlay)
    return paths


def scope_findings(target: Target, agents: Sequence[Agent]) -> list[Finding]:
    """Return the findings for *target*; machine-only rows only for machine scope."""
    found = _machine_findings(agents) if target.scope is Scope.MACHINE else []
    entries = StateStore(target.state_path, entry_type=StateEntry).load()
    found.extend(
        Finding(
            "agentkit.state-file-gone",
            Severity.WARNING,
            f"recorded file is gone: {entry.path}",
        )
        for entry in entries.values()
        if not (target.root / entry.path).exists()
    )
    for path in _overlay_paths(target):
        try:
            load_overlay(path)
        except (DocumentError, SourceError) as error:
            found.append(
                Finding("agentkit.overlay-invalid", Severity.ERROR, error.message)
            )
    found.extend(instruction_findings(target))
    return found


def check_machine(home: ToolHome) -> list[Finding]:
    """Return the machine scope's findings, for the lifecycle `doctor`."""
    target = resolve_target(
        Scope.MACHINE,
        repo=None,
        cwd=Path.cwd(),
        home=Path.home(),
        rnf_home=home.root,
    )
    return scope_findings(target, list(Agent))
