"""Artifact specs for the guard hook scripts (F3.1)."""

from __future__ import annotations

from rn_forge.commons.generation import ArtifactKind

from rn_forge.agentkit.adapters.spec import ArtifactSpec, Base


def _scripts(agent: str, names: tuple[str, ...]) -> tuple[ArtifactSpec, ...]:
    return tuple(
        ArtifactSpec(
            f"{agent}/hooks/{name}.sh",
            ArtifactKind.MANAGED,
            f"hooks/{agent}/{name}.sh",
            executable=True,
            base=Base.SHARE,
        )
        for name in names
    )


COMMON: tuple[ArtifactSpec, ...] = (
    ArtifactSpec(
        "_common/hooks/guard-core.sh",
        ArtifactKind.MANAGED,
        "hooks/_common/guard-core.sh",
        base=Base.SHARE,
    ),
)
CLAUDE: tuple[ArtifactSpec, ...] = _scripts(
    "claude",
    (
        "pre-bash-guard",
        "pre-write-protect",
        "session-compact-context",
        "user-prompt-secret-guard",
    ),
)
CODEX: tuple[ArtifactSpec, ...] = _scripts(
    "codex",
    ("pre-bash-guard", "pre-write-protect", "user-prompt-secret-guard"),
)
