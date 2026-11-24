"""Artifact specs for the packaged skills (F3.2)."""

from __future__ import annotations

from rn_forge.commons.generation import ArtifactKind

from rn_forge.agentkit.adapters.spec import ArtifactSpec

SKILLS = ("dev-team-orchestration", "sonar-cleanup")

CLAUDE: tuple[ArtifactSpec, ...] = tuple(
    ArtifactSpec(
        f".claude/skills/{name}/SKILL.md",
        ArtifactKind.MANAGED,
        f"skills/{name}/SKILL.md",
        skill=name,
    )
    for name in SKILLS
)
CODEX: tuple[ArtifactSpec, ...] = tuple(
    ArtifactSpec(
        f".codex/skills/{name}/SKILL.md",
        ArtifactKind.MANAGED,
        f"skills/{name}/SKILL.md",
        skill=name,
    )
    for name in SKILLS
)
