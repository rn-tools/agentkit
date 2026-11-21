"""Artifact specs for the instruction blocks and output style (F2.1)."""

from __future__ import annotations

from rn_forge.commons.fs.blocks import ManagedBlock
from rn_forge.commons.generation import ArtifactKind

from rn_forge.agentkit.adapters.spec import ArtifactSpec

BLOCK = ManagedBlock("rn-forge agentkit", comment="<!--")

CLAUDE: tuple[ArtifactSpec, ...] = (
    ArtifactSpec(
        ".claude/CLAUDE.md", ArtifactKind.BLOCK, "instructions/rules.md", block=BLOCK
    ),
    ArtifactSpec(
        ".claude/output-styles/concise.md",
        ArtifactKind.MANAGED,
        "instructions/concise.md.j2",
        template=True,
    ),
)
CODEX: tuple[ArtifactSpec, ...] = (
    ArtifactSpec(
        ".codex/AGENTS.md",
        ArtifactKind.BLOCK,
        "instructions/codex.md.j2",
        template=True,
        block=BLOCK,
    ),
)
