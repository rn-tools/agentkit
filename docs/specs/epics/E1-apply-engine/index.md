# E1 — Apply engine

|  |  |
| -- | -- |
| **State** | Active |
| **Start Date** | 2026-11-19 |

<!-- BEGIN derived features -->

| Feature | State | Iteration | Stories |
| -- | -- | -- | -- |
| [F1.1 — Sources and layers](F1.1-sources-and-layers.md) | Closed | release-1 | 1 Closed |
| [F1.2 — Owned key paths in shared settings files](F1.2-owned-key-paths.md) | Active | release-1 | 1 New · 1 Closed |
| [F1.3 — Commands](F1.3-commands.md) | Active | release-1 | 3 New |
| [F1.4 — Agent adapters](F1.4-agent-adapters.md) | New | release-1 | 1 New |

<!-- END derived features -->

The render, plan and apply pipeline on `rn_forge.commons.generation`, the source
layers (packaged defaults, user overlay, repository overlay), the adapter seam
for Claude Code and Codex, and the `apply`, `diff`, `plan` and `remove`
commands. It carries no content: instruction text is
[E2](../E2-instruction-files/index.md), hooks and skills are
[E3](../E3-asset-pack/index.md).
