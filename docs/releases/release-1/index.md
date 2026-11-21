# Release 1 — agentkit v1

|  |  |
| -- | -- |
| **Status** | shipped |
| **Start Date** | 2026-11-19 |
| **Finish Date** | 2026-11-21 |

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
| [F3.1 — Guard hooks](../../specs/epics/E3-asset-pack/F3.1-guard-hooks.md) | E3 | Closed |
| [F3.2 — Skills for both agents](../../specs/epics/E3-asset-pack/F3.2-skills.md) | E3 | Closed |
| [F4.1 — Product and install](../../specs/epics/E4-lifecycle-and-cutover/F4.1-product-and-install.md) | E4 | Closed |
| [F4.2 — Machine cutover](../../specs/epics/E4-lifecycle-and-cutover/F4.2-machine-cutover.md) | E4 | Closed |
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

E1 to E4 are closed. The cutover ran on this machine on 2026-11-21:
`agentkit doctor` exits 0 and `agentkit apply` reports all 18 artifacts
`unchanged`. A final commit carrying the runbook fixes from that run is still to
come.

## Commits

```bash
git log --oneline -E --grep='S[1-4]\.[0-9]+\.[0-9]+|F[1-4]\.[0-9]+'
```

Refreshed at the cut, 2026-11-21, before the final runbook-fix commit:

```text
ccdda01 S4.2.2 runbook
83d8252 S3.1.2, F3.1, E2, E3 close
d12d971 S4.2.2 brief
d2a09ab S4.3.1, F4.3 close
2ee904e S3.1.2 brief
95f9445 S2.2.4, F2.2 close
1e078b1 S1.4.2, F1.4, E1 close
9147f5e S2.2.4 story and brief
7867825 S1.4.2 brief
01f3fe8 S4.2.1
25f2218 S2.3.1, F2.3 close
4f700a8 S1.2.2, F1.2 close
32a179d S1.2.2, S2.3.1, S4.2.1 briefs
8056c43 S3.1.1
2400a46 S2.1.1, F2.1 close
159ae6a S3.2.1, F3.2 close
ca33eb0 S2.1.1, S3.1.1, S3.2.1 briefs
de02075 S2.2.3, F2.2 close
443cd83 S1.4.1
76a7784 S2.2.2
e5f9820 S2.2.1
bbcfbbd S1.4.1, S2.2 briefs
7d916f8 F1.4 split
3cf17b8 S1.3.3, F1.3 close
db37cd1 S1.3.3 brief
2c24025 S1.3.2
2d2d155 S1.3.2 brief
dd42789 S1.3.1
e32c85e S1.3.1 brief
d5880a9 S1.2.1
eb74c10 S4.1.1
4dc9fcb S1.2.1, S4.1.1 briefs
78e1ea8 S1.1.1
518499e S1.1.1 brief
```

## Exit criteria

- Every feature in Scope is `Closed`.
- The owner has run the cutover runbook on this machine: `agentkit doctor` exits
  0 and `agentkit apply` reports every artifact `unchanged`.
- `task validate` green.

## Shipped

| Deliverable | Version | Tag | Commit | Verification |
| -- | -- | -- | -- | -- |
| agentkit | — | — | final runbook-fix commit on `feature/release-1`, not yet made | `agentkit doctor` exit 0 and `agentkit apply` all 18 artifacts `unchanged` on this machine, 2026-11-21 |
