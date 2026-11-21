"""Repository-scope artifacts, rendered from the `[repo]` overlay table.

These belong to the scope rather than to an agent: they render at repository
scope whatever agents are selected, and never at machine scope.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from rn_forge.commons.fs.blocks import ManagedBlock
from rn_forge.commons.generation import Artifact, ArtifactKind
from rn_forge.commons.lang.collections import MergeResult

from rn_forge.agentkit.sources import Scope, SourceError
from rn_forge.agentkit.targets import Target

AGENTS_BLOCK = ManagedBlock("rn-forge agentkit", comment="<!--")
CLAUDE_SEED = "@AGENTS.md\n"
_KEYS = ("worktree_root", "shared_checkout", "story_workflow")


def _validate(table: Mapping[str, Any]) -> None:
    for key, value in table.items():
        if key not in _KEYS:
            raise SourceError(
                "[repo] {!r}: unknown key; expected one of {}",
                key,
                ", ".join(_KEYS),
            )
        expected = bool if key == "shared_checkout" else str
        if type(value) is not expected:
            raise SourceError(
                "[repo] {!r}: expected {}, got {!r}", key, expected.__name__, value
            )


def agents_block(table: Mapping[str, Any], repo_name: str) -> str:
    """Build the body of agentkit's AGENTS.md block; empty when nothing is set."""
    lines: list[str] = []
    if worktree_root := table.get("worktree_root"):
        lines.append(
            "- Worktrees: create each one under "
            f"`{worktree_root.replace('{repo}', repo_name)}`."
        )
    if table.get("shared_checkout") is True:
        lines.append(
            "- Shared checkout: commit by explicit path, never `git add -A`, "
            "and re-check HEAD before committing."
        )
    if story_workflow := table.get("story_workflow"):
        lines.append(f"- Story workflow: {' '.join(story_workflow.split())}")
    if not lines:
        return ""
    return "## Agent workflow\n\n" + "\n".join(lines) + "\n"


def render(target: Target, sources: MergeResult) -> list[Artifact]:
    """Render the repository-scope artifacts for *target*.

    At repository scope this is the optional AGENTS.md block, then a CLAUDE.md
    seed that is written only when the file is absent.

    Raises:
        SourceError: A `[repo]` key is unknown or has the wrong type.
    """
    if target.scope is not Scope.REPO:
        return []
    table = sources.config.get("repo", {})
    _validate(table)
    body = agents_block(table, target.root.name)
    artifacts: list[Artifact] = []
    if body:
        artifacts.append(Artifact("AGENTS.md", ArtifactKind.BLOCK, body, AGENTS_BLOCK))
    artifacts.append(Artifact("CLAUDE.md", ArtifactKind.SEEDED, CLAUDE_SEED))
    return artifacts
