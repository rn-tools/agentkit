"""Advisory checks that read a whole instruction file, body included."""

from __future__ import annotations

import re
from dataclasses import dataclass

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.blocks import ManagedBlock

from rn_forge.agentkit.adapters.instructions import BLOCK
from rn_forge.agentkit.sources import Scope
from rn_forge.agentkit.targets import Target

PATHS = {
    Scope.MACHINE: (".claude/CLAUDE.md", ".codex/AGENTS.md"),
    Scope.REPO: ("AGENTS.md", "CLAUDE.md"),
}
PLACEHOLDERS: tuple[str, ...] = (
    "Replace this line",
    "Replace this section",
    "Instructions that only Claude Code should follow go here",
)
_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
_CLAUDE_POINTER = re.compile(r"\]\((?:\./)?CLAUDE\.md[)#]|[Rr]ead `CLAUDE\.md`")
_KILN = ManagedBlock("rn-forge kiln", comment="<!--")


@dataclass(frozen=True, slots=True)
class Suggestion:
    """One advisory suggestion about an instruction file."""

    path: str
    line: int
    code: str
    message: str


def _review_file(path: str, text: str, *, check_imports: bool) -> list[Suggestion]:
    try:
        BLOCK.extract(text)
    except AppException:
        return [
            Suggestion(
                path,
                1,
                "review.block-malformed",
                "agentkit's block markers are malformed; run agentkit doctor",
            )
        ]

    suggestions: list[Suggestion] = []
    headings: dict[str, list[tuple[int, str]]] = {
        "body": [],
        "agentkit": [],
        "kiln": [],
    }
    imports: dict[str, int] = {}
    in_agentkit = in_kiln = fenced = False
    check_pointers = path.rsplit("/", 1)[-1] == "AGENTS.md"
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped in (BLOCK.begin, BLOCK.end):
            in_agentkit = stripped == BLOCK.begin
            continue
        if stripped in (_KILN.begin, _KILN.end):
            in_kiln = stripped == _KILN.begin
            continue
        region = "agentkit" if in_agentkit else "kiln" if in_kiln else "body"

        if line.startswith(("```", "~~~")):
            fenced = not fenced
        elif not fenced:
            if match := _HEADING.match(line):
                headings[region].append((number, match.group(1).strip()))
            if check_pointers and _CLAUDE_POINTER.search(line):
                suggestions.append(
                    Suggestion(
                        path,
                        number,
                        "review.agents-points-at-claude",
                        "AGENTS.md points at CLAUDE.md, which Codex cannot follow",
                    )
                )
        if check_imports and stripped == "@AGENTS.md":
            imports.setdefault(region, number)
        if region == "body":
            for pattern in PLACEHOLDERS:
                if pattern in line:
                    suggestions.append(
                        Suggestion(
                            path,
                            number,
                            "review.placeholder",
                            f"line still reads as template text: {pattern!r}",
                        )
                    )
                    break

    agentkit_headings = {heading for _, heading in headings["agentkit"]}
    kiln_headings = {heading for _, heading in headings["kiln"]}
    for number, heading in headings["body"]:
        if heading in agentkit_headings:
            block = "agentkit"
        elif heading in kiln_headings:
            block = "kiln"
        else:
            continue
        suggestions.append(
            Suggestion(
                path,
                number,
                "review.heading-duplicated",
                f"heading {heading!r} repeats one in {block}'s block",
            )
        )
    for number, heading in headings["agentkit"]:
        if heading in kiln_headings:
            suggestions.append(
                Suggestion(
                    path,
                    number,
                    "review.heading-duplicated",
                    f"heading {heading!r} in agentkit's block repeats one in kiln's block",
                )
            )

    if check_imports:
        if not imports:
            suggestions.append(
                Suggestion(
                    path,
                    1,
                    "review.claude-import-missing",
                    "CLAUDE.md does not import @AGENTS.md",
                )
            )
        elif "body" in imports and "agentkit" in imports:
            suggestions.append(
                Suggestion(
                    path,
                    imports["body"],
                    "review.import-repeated",
                    "@AGENTS.md is in both the body and agentkit's block; delete it from the body",
                )
            )

    return sorted(
        suggestions, key=lambda suggestion: (suggestion.line, suggestion.code)
    )


def review(target: Target) -> list[Suggestion]:
    """Return the suggestions for the target scope's instruction files."""
    suggestions: list[Suggestion] = []
    for path in PATHS[target.scope]:
        try:
            text = (target.root / path).read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        suggestions.extend(
            _review_file(
                path,
                text,
                check_imports=target.scope is Scope.REPO and path == "CLAUDE.md",
            )
        )
    return suggestions
