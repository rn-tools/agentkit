# Per-repository native config

[Back to the ideas](index.md)

agentkit would manage the agents' own config files inside a repository, next to
the machine-level files it manages today. This page maps where that meets kiln's
files and lists the decisions to settle before the idea becomes an epic.

The instruction-file rule this page first held, blocks only, is now
[E5](../epics/E5-blocks-only-instruction-files/index.md) and kiln's matching
epic.

## Native config files

kiln's standard says it neither writes nor reads `.claude/**` or `.codex/**`,
and ADR-0003 says ownership is complete or absent. agentkit can own keys in
these files with no conflict with kiln. kiln's generated `standard.md` should
name agentkit as their owner, so an agent reading the standard does not treat
agentkit's keys as hand edits.

| File | Shared or personal | What agentkit would own |
| -- | -- | -- |
| `.claude/settings.json` | committed, shared | KEYS: `permissions.allow` for the repository's `task` verbs, additions to `permissions.deny`, and `env` |
| `.claude/settings.local.json` | personal, not committed | nothing: the owner's machine-level choices already live in `~/.claude` |
| `.codex/config.toml` | committed; Codex loads it only for a trusted project | KEYS: sandbox writable roots, such as the `uv` caches, and the approval policy |
| `.codex/hooks.json` | committed | nothing yet: see the trust note below |

### Constraints found

- **Hook trust is per path.** Codex records a `trusted_hash` for each
  `hooks.json` in `~/.codex/config.toml`, keyed by its absolute path. A
  repository `hooks.json` must be trusted again in every clone and worktree,
  and again after every change. Guard hooks are better kept machine-level.
- **Committed files must not point at the machine.** Repository hooks that call
  `$RNF_HOME/share/agentkit/...` break in CI and on machines without agentkit.
  Anything committed has to work without agentkit installed.
- **Repository keys are shared state.** A KEYS artifact in a committed file
  records its state per clone. If two clones apply different overlays, the
  result shows up as a git diff, not as drift. The overlay that feeds
  committed keys must itself be committed. That overlay is
  `.rn-forge/agentkit/config.toml`, which already exists.

### The post-edit format hook

macsetup ran a formatter after every edit. In a `task` repository, `task format`
and `task lint` are the gate, and a per-edit hook runs a second formatter with
its own settings, so files change under the agent. Recommendation: no post-edit
format hook in `task` repositories.

## Proposed shape

1. agentkit owns keys in `.claude/settings.json` and `.codex/config.toml` in a
   repository as KEYS artifacts. They are fed by the `[claude]` and `[codex]`
   tables of `.rn-forge/agentkit/config.toml`, and written only when those
   tables are set.
1. Hooks, skills and personal settings stay machine-level.
1. kiln, in its own repository, names agentkit as the owner of the agent keys in
   `.claude/**` and `.codex/**`.

## Open decisions

- Does a repository get `permissions.allow` entries for its `task` verbs by
  default, or only when the overlay asks for them?
