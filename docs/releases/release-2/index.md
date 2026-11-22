# Release 2 — Blocks-only instruction files

|  |  |
| -- | -- |
| **Status** | in progress |
| **Start Date** | 2026-11-22 |

agentkit writes and checks only its own blocks in instruction files: a
repository `CLAUDE.md` gets the `@AGENTS.md` import as a block, `doctor` stops
reading body text, and a new advisory `agentkit review` takes over the checks
that read it.

## Entry criteria

- ADR-0002 revised 2026-11-21.
- Release 1 shipped.

## Scope

<!-- BEGIN derived scope -->

| Feature | Epic | State |
| -- | -- | -- |
| [F5.1 — agentkit writes and checks only its blocks](../../specs/epics/E5-blocks-only-instruction-files/F5.1-blocks-only.md) | E5 | Closed |
| [F5.2 — `agentkit review`](../../specs/epics/E5-blocks-only-instruction-files/F5.2-review-command.md) | E5 | New |

<!-- END derived scope -->

## Exit criteria

- Every feature in Scope is `Closed`.
- `task validate` green.

## Shipped

| Deliverable | Version | Tag | Commit | Verification |
| -- | -- | -- | -- | -- |
