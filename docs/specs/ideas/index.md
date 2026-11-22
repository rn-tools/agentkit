# Ideas

Ideas not yet agreed as this repository's work. An entry takes no ID and no
state, and does not authorize starting anything. An idea that needs more than
its row has a page in this folder, named after the row and linked from its
**Idea** cell. Promoting one moves its page, or its row's summary, into a new
epic or feature and deletes both; a dropped idea's row and page are deleted too.

[Back to the specs](../index.md)

| Idea | Summary | Source |
| -- | -- | -- |
| Capture native hand edits into the user overlay | `agentkit capture`: read owned keys/blocks that drifted and write them to the user overlay instead of overwriting (never into the package) | agentkit v0 review, 2026-11-14 |
| [Per-repository native config](per-repository-native-config.md) | `.claude/settings.local.json`, `.codex/config.toml`, `.codex/hooks.json` per repo, as macsetup used; and whether a post-edit format hook belongs in task-driven repos at all | agentkit v0 review, 2026-11-14 |
| Third-party adapters | entry-point discovery for agents beyond Claude Code and Codex | agentkit v0 review, 2026-11-14 |
| Codex allow rules | managing `~/.codex/rules/default.rules` prefix rules alongside Claude allow lists | agentkit v0 review, 2026-11-14 |
| More packaged skills | `python-simplify` and `gh-fix` from the old pack, which the owner removed from the machine | agentkit v0 review, 2026-11-14 |
| Implementer and reviewer agents | the agentic-kit draft's Sonnet implementer and Opus reviewer subagents and `/spec` `/story` `/release` skills, reconciled with `dev-team-orchestration` and kiln's spec layout | agentkit v0 review, 2026-11-14 |
