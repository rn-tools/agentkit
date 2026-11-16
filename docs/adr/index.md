# Decisions

Durable choices that constrain what agentkit writes and how. Each record opens
with the decision, what follows from it, and what it influences; alternatives
and history are at the bottom. Scope and rollout work belong in
[specs](../specs/index.md).

| # | Decision | Scope |
| -- | -- | -- |
| [0001](ADR-0001.md) | agentkit configures agents, and owns no repository prose | what agentkit writes, at machine and repository level |
| [0002](ADR-0002.md) | Instruction files: agentkit owns a fenced block, never the body | `CLAUDE.md` and `AGENTS.md` |
| [0003](ADR-0003.md) | Native settings files are shared; agentkit owns key paths | structured native config |
| [0004](ADR-0004.md) | Built on the commons generation engine; drift blocks | rendering, reconciling and state |
