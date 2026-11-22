# Building stories

- Always build a story with a Sonnet subagent; Opus reviews it. Never hand a
  story to Codex.

<!-- BEGIN rn-forge agentkit -->

## Bias to action

- To implement stories that have briefs, use the `dev-team-orchestration` skill:
  an implementer the user chooses (Codex, Sonnet or another model) builds each
  story in its own worktree; you review, close and merge.

## Model routing and token economy

- Explicitly select the lowest-cost available model capable of each delegated
  task. Never let routine workers silently inherit the higher model.

<!-- END rn-forge agentkit -->
