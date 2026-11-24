"""Guard hook scripts and their registrations (F3.1)."""

from __future__ import annotations

import os
from pathlib import Path

from rn_forge.commons.generation import ArtifactKind

from rn_forge.agentkit.adapters.spec import ArtifactSpec, Base


def share_prefix() -> str:
    """Return the share directory prefix for registered hook commands."""
    value = os.environ.get("RNF_HOME")
    if not value:
        return "$HOME/.rn-forge/share/agentkit"
    return (Path(value).expanduser() / "share" / "agentkit").as_posix()


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
CODEX: tuple[ArtifactSpec, ...] = (
    *_scripts(
        "codex",
        ("pre-bash-guard", "pre-write-protect", "user-prompt-secret-guard"),
    ),
    ArtifactSpec(
        ".codex/hooks.json",
        ArtifactKind.MANAGED,
        "hooks/codex/hooks.json.j2",
        template=True,
    ),
)
