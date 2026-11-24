# E5 — Blocks-only instruction files

|  |  |
| -- | -- |
| **State** | Closed |
| **Start Date** | 2026-11-22 |
| **Closed Date** | 2026-11-23 |

<!-- BEGIN derived features -->

| Feature | State | Iteration | Stories |
| -- | -- | -- | -- |
| [F5.1 — agentkit writes and checks only its blocks](F5.1-blocks-only.md) | Closed | release-2 | 2 Closed |
| [F5.2 — `agentkit review`](F5.2-review-command.md) | Closed | release-2 | 2 Closed |

<!-- END derived features -->

agentkit stops owning any part of an instruction file outside its own fenced
blocks ([ADR-0002](../../../adr/ADR-0002.md), revised 2026-11-21). A repository
`CLAUDE.md` gets the `@AGENTS.md` import as an agentkit block instead of a
seeded body. `doctor` reports drift only inside agentkit's blocks, and a new
advisory command, `agentkit review`, takes over the checks that read the owner's
text. kiln makes the matching change to its own block and seeds in its epic
"Instruction files carry blocks only".

## Decisions

- **Block order in a repository `AGENTS.md` is not fixed** (owner, 2026-11-23).
  Each tool reads and checks only inside its own markers, so the order causes
  no drift, and an existing block is updated in place, so applies never
  reorder it. kiln's block comes first by construction: kiln writes
  `AGENTS.md` when it generates a repository, and agentkit appends its block
  afterwards. Enforcing an order would mean one tool moving the other's block,
  which ADR-0002 rules out. A block that is removed and re-added goes to the
  end, which is accepted.
