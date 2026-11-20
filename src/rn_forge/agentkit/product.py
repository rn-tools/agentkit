"""This tool as the lifecycle verbs see it.

`[lifecycle]` in `.rn-forge/kiln/config.toml` names `PRODUCT`; the verbs
themselves — `install`, `upgrade`, `uninstall`, `cleanup`, `status`, `doctor` —
come from `rn-forge-tooling`.
"""

from __future__ import annotations

from collections.abc import Sequence
from importlib.metadata import version

from rn_forge.commons.findings import Finding, Severity
from rn_forge.tooling.install import Check, PythonTool, ToolHome


def check_home(home: ToolHome) -> list[Finding]:
    """Report where this tool is, or would be, installed."""
    return [
        Finding(
            "agentkit.home",
            Severity.INFO,
            f"home is {home.product_dir}",
        ),
    ]


class Tool(PythonTool):
    """Install the AgentKit console script and check its home."""

    def checks(self) -> Sequence[Check]:
        """Check the install's home."""
        return (check_home,)


PRODUCT = Tool(
    name="agentkit",
    version=version("agentkit"),
    repo="rn-tools/agentkit",
)
