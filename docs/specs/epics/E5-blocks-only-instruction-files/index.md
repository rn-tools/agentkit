# E5 — Blocks-only instruction files

|  |  |
| -- | -- |
| **State** | Active |
| **Start Date** | 2026-11-22 |

<!-- BEGIN derived features -->

| Feature | State | Iteration | Stories |
| -- | -- | -- | -- |
| [F5.1 — agentkit writes and checks only its blocks](F5.1-blocks-only.md) | Closed | release-2 | 2 Closed |
| [F5.2 — `agentkit review`](F5.2-review-command.md) | Active | release-2 | 1 New · 1 Closed |

<!-- END derived features -->

agentkit stops owning any part of an instruction file outside its own fenced
blocks ([ADR-0002](../../../adr/ADR-0002.md), revised 2026-11-21). A repository
`CLAUDE.md` gets the `@AGENTS.md` import as an agentkit block instead of a
seeded body. `doctor` reports drift only inside agentkit's blocks, and a new
advisory command, `agentkit review`, takes over the checks that read the owner's
text. kiln makes the matching change to its own block and seeds in its epic
"Instruction files carry blocks only".

## Open questions

- Is the order of kiln's and agentkit's blocks in a repository `AGENTS.md`
  fixed? The proposal is kiln's block first, because it states the standard
  agentkit's block builds on. Today the order is whichever tool applied first.
