# Release 1 — agentkit v1

|  |  |
| -- | -- |
| **Status** | in progress |
| **Start Date** | 2026-11-19 |

The rebuilt agentkit, which replaces v0.5.0. It brings the apply engine over the
commons generation engine, agentkit's blocks in machine and repository
instruction files, the guard hooks and skills for Claude Code and Codex, the
lifecycle product, this machine's cutover from v0, and this repository
dogfooding its own repository block.

## Entry criteria

- ADR-0001 to ADR-0004 accepted.
- `task validate` green on the kiln scaffold.

## Scope

<!-- BEGIN derived scope -->

| Feature | Epic | State |
| -- | -- | -- |
| [F1.1 — Sources and layers](../../specs/epics/E1-apply-engine/F1.1-sources-and-layers.md) | E1 | Closed |
| [F1.2 — Owned key paths in shared settings files](../../specs/epics/E1-apply-engine/F1.2-owned-key-paths.md) | E1 | Closed |
| [F1.3 — Commands](../../specs/epics/E1-apply-engine/F1.3-commands.md) | E1 | Closed |
| [F1.4 — Agent adapters](../../specs/epics/E1-apply-engine/F1.4-agent-adapters.md) | E1 | Closed |
| [F2.1 — Machine instruction blocks](../../specs/epics/E2-instruction-files/F2.1-machine-instruction-blocks.md) | E2 | Closed |
| [F2.2 — Repository block and CLAUDE.md seed](../../specs/epics/E2-instruction-files/F2.2-repository-block.md) | E2 | Closed |
| [F2.3 — Instruction doctor checks](../../specs/epics/E2-instruction-files/F2.3-instruction-doctor-checks.md) | E2 | Closed |
| [F3.1 — Guard hooks](../../specs/epics/E3-asset-pack/F3.1-guard-hooks.md) | E3 | Active |
| [F3.2 — Skills for both agents](../../specs/epics/E3-asset-pack/F3.2-skills.md) | E3 | Closed |
| [F4.1 — Product and install](../../specs/epics/E4-lifecycle-and-cutover/F4.1-product-and-install.md) | E4 | Closed |
| [F4.2 — Machine cutover](../../specs/epics/E4-lifecycle-and-cutover/F4.2-machine-cutover.md) | E4 | Active |
| [F4.3 — Repository rollout](../../specs/epics/E4-lifecycle-and-cutover/F4.3-repository-rollout.md) | E4 | Closed |

<!-- END derived scope -->

## Decisions

- [ADR-0001](../../adr/ADR-0001.md): agentkit configures agents and owns no
  repository prose. Accepted.
- [ADR-0002](../../adr/ADR-0002.md): in instruction files, agentkit owns a
  fenced block and never the body. Accepted.
- [ADR-0003](../../adr/ADR-0003.md): native settings files are shared, and
  agentkit owns key paths in them. Accepted.
- [ADR-0004](../../adr/ADR-0004.md): agentkit is built on the commons generation
  engine, and drift blocks an apply. Accepted.

## Breaking changes

The v0 layout (`$RNF_HOME/agentkit/v<ver>/`) and v0 state file are retired. The
cutover runbook (F4.2) moves this machine across.

## Progress

Closed: F1.1, F1.2, F1.3, F2.1, F2.2, F3.2 and F4.1. rn-forge-commons 0.10.1,
with the `keys` kind, is on PyPI and agentkit's floor; F1.4's settings artifacts
(S1.4.2) and the hook registration that names them (S3.1.2) are next.

## Commits

```bash
git log --oneline -E --grep='S[1-4]\.[0-9]+\.[0-9]+|F[1-4]\.[0-9]+'
```

Refreshed at the cut.

## Exit criteria

- Every feature in Scope is `Closed`.
- The owner has run the cutover runbook on this machine: `agentkit doctor` exits
  0 and `agentkit apply` reports every artifact `unchanged`.
- `task validate` green.

## Shipped

| Deliverable | Version | Tag | Commit | Verification |
| -- | -- | -- | -- | -- |
