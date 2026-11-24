"""This tool as the lifecycle verbs see it.

`[lifecycle]` in `.rn-forge/kiln/config.toml` names `PRODUCT`; the verbs
themselves — `install`, `upgrade`, `uninstall`, `cleanup`, `status`, `doctor` —
come from `rn-forge-tooling`.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from importlib.metadata import version
from pathlib import Path

from rn_forge.commons.findings import Finding, Severity
from rn_forge.tooling.install import Check, PythonTool, ToolHome

from rn_forge.agentkit.cutover import check_v0
from rn_forge.agentkit.findings import check_machine


def share_dir(home: ToolHome) -> Path:
    """Return the share dir, which `uninstall` leaves in place."""
    return home.root / "share" / "agentkit"


def check_share_dir(home: ToolHome) -> list[Finding]:
    """Report an error when the share dir cannot be written to."""
    path = share_dir(home)
    target = path
    if not path.exists():
        target = next(p for p in path.parents if p.exists())
    if target.is_dir() and os.access(target, os.W_OK):
        return []
    return [
        Finding(
            "agentkit.share-unwritable",
            Severity.ERROR,
            f"share dir is not writable: {path}",
        ),
    ]


class Tool(PythonTool):
    """Install the AgentKit console script; check its share dir and the machine scope."""

    def checks(self) -> Sequence[Check]:
        """Check the share dir, machine scope, and v0 install and state."""
        return (check_share_dir, check_machine, check_v0)


PRODUCT = Tool(
    name="agentkit",
    version=version("agentkit"),
    repo="rn-tools/agentkit",
)
