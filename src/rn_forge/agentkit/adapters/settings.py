"""Machine-scope settings keys owned by each agent adapter (F1.4)."""

from __future__ import annotations

from rn_forge.commons.generation import ArtifactKind

from rn_forge.agentkit.adapters.spec import ArtifactSpec

CLAUDE: tuple[ArtifactSpec, ...] = (
    ArtifactSpec(
        ".claude/settings.json",
        ArtifactKind.KEYS,
        source="hooks/claude/settings-hooks.json.j2",
        template=True,
        keys=(
            "effortLevel",
            "extraKnownMarketplaces",
            "hooks",
            "outputStyle",
            "permissions.deny",
        ),
    ),
)
CODEX: tuple[ArtifactSpec, ...] = (
    ArtifactSpec(
        ".codex/config.toml",
        ArtifactKind.KEYS,
        "",
        keys=(
            "approval_policy",
            "features.hooks",
            "model_reasoning_effort",
            "model_reasoning_summary",
            "personality",
            "profiles.deep",
            "profiles.trusted",
            "sandbox_mode",
            "sandbox_workspace_write.network_access",
        ),
    ),
)
