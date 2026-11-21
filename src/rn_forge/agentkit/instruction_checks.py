"""Warnings about imports, headings and canonical instruction files."""

from __future__ import annotations

import re
from collections.abc import Iterator

from rn_forge.commons.findings import Finding, Severity

from rn_forge.agentkit.adapters.instructions import BLOCK
from rn_forge.agentkit.sources import Scope
from rn_forge.agentkit.targets import Target

_PATHS = {
    Scope.MACHINE: (".claude/CLAUDE.md", ".codex/AGENTS.md"),
    Scope.REPO: ("AGENTS.md", "CLAUDE.md"),
}
_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")


def _headings(text: str) -> Iterator[str]:
    fenced = False
    for line in text.splitlines():
        if line.startswith(("```", "~~~")):
            fenced = not fenced
        elif not fenced and (match := _HEADING.match(line)):
            yield match.group(1).strip()


def _duplicate_headings(text: str) -> Iterator[str]:
    block = BLOCK.extract(text)
    if block is None:
        return
    body_headings = set(_headings(BLOCK.remove(text)))
    for heading in _headings(block):
        if heading in body_headings:
            body_headings.remove(heading)
            yield heading


def instruction_findings(target: Target) -> list[Finding]:
    """Check the instruction files for the target scope.

    Raises:
        AppException: An instruction file has malformed agentkit block markers.
    """
    found: list[Finding] = []
    for path in _PATHS[target.scope]:
        file = target.root / path
        try:
            text = file.read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
        if path == "CLAUDE.md" and not any(
            line.strip() == "@AGENTS.md" for line in text.splitlines()
        ):
            found.append(
                Finding(
                    "agentkit.claude-import-missing",
                    Severity.WARNING,
                    f"{path} does not import @AGENTS.md",
                )
            )
        found.extend(
            Finding(
                "agentkit.heading-duplicated",
                Severity.WARNING,
                f"{path}: heading {heading!r} is in both the body and agentkit's block",
            )
            for heading in _duplicate_headings(text)
        )
        if file.name == "AGENTS.md" and "Read `CLAUDE.md` now" in text:
            found.append(
                Finding(
                    "agentkit.agents-points-at-claude",
                    Severity.WARNING,
                    f"{path} points at CLAUDE.md as canonical; AGENTS.md is canonical",
                )
            )
    return found
