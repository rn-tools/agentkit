"""The instruction-file check doctor runs: malformed agentkit markers."""

from __future__ import annotations

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.findings import Finding, Severity

from rn_forge.agentkit.adapters.instructions import BLOCK
from rn_forge.agentkit.review import PATHS
from rn_forge.agentkit.targets import Target


def instruction_findings(target: Target) -> list[Finding]:
    """Check the instruction files for the target scope."""
    found: list[Finding] = []
    for path in PATHS[target.scope]:
        file = target.root / path
        try:
            text = file.read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
        try:
            BLOCK.extract(text)
        except AppException as error:
            found.append(
                Finding(
                    "agentkit.block-malformed",
                    Severity.ERROR,
                    f"{path}: {error.message}",
                )
            )
    return found
