---
name: dev-team-orchestration
description: Orchestrate implementation of briefed stories by a chosen implementer (Codex, a Sonnet subagent, or another model's CLI), each in its own git worktree, with Claude as reviewer who code-reviews, closes and merges one story at a time. Use when the user asks to implement a set of stories or a wave of an epic through other agents, hand stories to Codex/Sonnet, or "orchestrate the implementation".
---

# Dev team orchestration

Claude is the lead: it schedules stories, starts implementers, reviews their
diffs, closes each story and merges it. Implementers write the code and run the
full gate. Claude never re-implements a story, and spends its tokens on review.

## Inputs

Settle these from the request, the repo and memory before starting. Ask only
for what cannot be found.

| Input | Default |
| -- | -- |
| Stories | named by the user; each must have a brief |
| Implementer | `codex`, `sonnet` or `other` (the user supplies a command); ask if not said |
| Base branch | the current release/feature branch, never `main` unless it is the working branch |
| Gate | the repo's full validation verb (e.g. `task validate`); read the repo's instructions |
| Targeted re-run | the tests the brief names under its review re-run |
| Parallel runs | 3 |
| Git | local only: no push, PR or tag unless asked |

## Preconditions

- **Each story has a brief** whose decisions are settled. The format comes from
  the repo, e.g. kiln's `specs/_structure.md` rule: `_briefs/<story>.md` with
  Goal, Settled, Current behaviour, Change, Tests first, Out of scope,
  Validation, Review re-run, Rules and Result. A story without one gets a brief
  first.
- **Validation runs the full suite once.** It is setup, format, then the
  gate (e.g. `task validate`), with no separate full `task test` step, because
  the gate already runs every suite. Targeted tests go in a separate
  "while iterating" command, scoped to one package (in pykit:
  `PYTEST_ADDOPTS='<node ids>' task test PACKAGE_DIRS=packages/<pkg>`).
- **"Current behaviour" states the observed failure.** Run or read the code so
  the brief says how each new test fails before the change, e.g. a 422 problem
  rather than a crash. A wrong prediction makes a careful implementer stop and
  ask, which costs a whole run. If the brief still asks the reader to decide something, the decision
  is its own story, settled with the user.
- **Commit the briefs on the base branch**, because a worktree only sees
  committed files.
- **The main checkout is clean.**

## Scheduling

- Run at most one story per package or module area at a time. Stories in
  different areas run in parallel, up to the cap.
- Follow the epic's order and each story's `Depends on`.
- Decision stories may run alongside build stories: they produce reproduction
  tests and an options comparison, not a fix.

## Per story

### 1. Worktree

```bash
git worktree add -b <prefix>/<story> ../<repo>-wt/<story> <base branch HEAD sha>
```

Always pass the base SHA explicitly. Tool-managed worktrees (the Agent tool's
`isolation: "worktree"`, or a Codex app worktree) may start from `main`.

### 2. Implementer prompt

Write it to `../<repo>-wt/<story>.prompt.md`:

```text
Implement story <story> in this worktree.

Your instructions are the brief at <brief path>. Read it fully, plus the repo's
agent instructions (AGENTS.md or equivalent), before changing anything.

- Follow the brief exactly. Write the tests under "Tests first" before the
  change, and confirm each fails as the brief says.
- Use only the repo's sanctioned entrypoint (e.g. task verbs); never invoke
  the underlying tools directly. <repo-specific environment notes, e.g.
  "unset VIRTUAL_ENV">
- Do not commit, push or create branches. Do not edit any spec page except the
  brief's ## Result section, any generated file, or any dependency.
- Run the brief's Validation steps in order. Fix failures your change caused.
  If a failure existed before your change or lies outside the brief's scope,
  stop and report it instead of working around it.
- If the brief is wrong or ambiguous, stop, write the question in ## Result,
  and end.
- When done, fill in ## Result: each validation command with its exit code,
  the files changed, and any deviation from the brief with its reason.

End with a three-line summary: status (done or blocked), validation exit
codes, and files changed.
```

### 3. Start the implementer

Run it in the background, and do not poll; the harness reports when it exits.

**codex** (OpenAI quota; costs Claude no tokens):

```bash
codex exec -C ../<repo>-wt/<story> -s workspace-write \
  -c 'approval_policy="never"' -c sandbox_workspace_write.network_access=true \
  --add-dir <each toolchain cache the gate writes to> \
  -o ../<repo>-wt/<story>.last.txt - < ../<repo>-wt/<story>.prompt.md
```

- Toolchain caches: for `uv`, `~/Library/Caches/uv` and `~/.local/share/uv`.
  For node, the npm, pnpm or Nx cache directories. Find them with the tool's
  own command, e.g. `uv cache dir`.
- Network access is needed whenever setup or lint downloads anything.
- Prefix `env -u <VAR>` for environment variables that leak from Claude's
  shell, such as `VIRTUAL_ENV`.
- Send stdout and stderr to `../<repo>-wt/<story>.codex.log`, appending
  (`>>`). The log header holds `session id: <uuid>`. Read only that line, and
  record the id per story; never read the rest of the log.
- **Resume, never restart.** A follow-up, a reviewer ruling on a blocked
  story, or a run cut off by quota resumes the story's own session, so Codex
  keeps the brief, the code it read and its partial work. A fresh `exec`
  re-reads everything and repeats the validation, which in practice cost a
  whole second run each time. `resume` accepts neither `-C` nor `-s` nor
  `--add-dir`, so run it from the worktree and repeat the sandbox settings
  with `-c`:

  ```bash
  cd ../<repo>-wt/<story> && env -u VIRTUAL_ENV codex exec resume <session-id> \
    -c 'sandbox_mode="workspace-write"' -c 'approval_policy="never"' \
    -c sandbox_workspace_write.network_access=true \
    -c 'sandbox_workspace_write.writable_roots=["<cache>", ...]' \
    -o ../<story>.last.txt "<fixes or ruling>" >> ../<story>.codex.log 2>&1
  ```

  Resume by id, not with `--last`: with parallel runs, the newest session may
  belong to another story. Start a fresh `exec` only when the session cannot
  be found. Then tell Codex its earlier partial work is in the worktree.
- **Quota:** a usage-limit stop appears as a non-zero exit, an empty `-o` file
  and a `usage limit` line in the log; `grep -c "usage limit"` checks for it
  without reading the transcript. Do not restart; wait until the user confirms
  the quota is back, then resume each interrupted session with "continue where
  you stopped".

**sonnet** (Claude quota; roughly 50–150k tokens per story):

- Start it with the Agent tool: `model: "sonnet"`, `run_in_background: true`,
  and no `isolation`.
- The prompt starts with `Work only in <absolute worktree path>; cd there
  first.`, followed by the implementer prompt.
- Follow-up: send it a message with the fixes, which keeps its context.

**other** (the user supplies the command):

- Run the user's command template, with the worktree, the prompt file and the
  output file substituted in.
- Example for another Claude model:
  `claude -p --model <model> --add-dir <worktree> < <prompt file> > <out file>`,
  run from the worktree.
- Confirm the command with the user once, before the first run.

### 4. Review

Read only the implementer's final message (the `-o` or out file, or the
subagent's report), the brief's `## Result`, and the diff. Never read a
transcript.

1. **Result:** every validation step shows exit 0. A missing step or a
   non-zero exit sends the story back.
2. **Diff:** `git -C <worktree> diff --stat`, then file by file. Review it
   against the brief and the story's acceptance: correctness, the tests written
   first, scope, the repo's rules on docstrings, comments and boundaries, and
   no edits to generated files.
3. **Findings:** send them back to the same implementer session with each fix
   named. Edit yourself only when the fix is a line or two.
4. **Blocked:** if the implementer reports a pre-existing failure or an
   ambiguous brief, stop and ask the user.

### 5. Close and merge (build story)

In the worktree:

1. Flip the story to `Closed (<date>)`.
2. Copy any contract settled in the brief into the story's acceptance, and add
   at most one outcome line.
3. Delete the brief, run the repo's derive or generate step, then its format
   verb. Spec edits you commit unformatted fail the next implementer's gate,
   which costs it a blocked run.
4. Commit, with the subject being the story ID and the attribution trailer.
5. If the base branch moved, rebase. If the rebase brought in other changes,
   run the targeted re-run, or the repo's test verb if it cannot target.
6. From the main checkout, `git merge --ff-only <prefix>/<story>`.
7. `git worktree remove ../<repo>-wt/<story>`, then delete the branch.

The implementer already ran the full gate on that exact tree, so a
fast-forward merge needs no re-run.

### 6. Decision stories

1. Review the reproduction tests and the options comparison in `## Result`.
2. Put the choice to the user, with your recommendation.
3. Once they decide, write the ADR or the settled acceptance, and close the
   story the same way.
4. Write briefs for the stories it unblocks.

## Feature close

When a feature's last story merges:

- Run the full gate once on the base branch.
- Close the feature per the repo's spec rules.

## Reporting

- **After each story:** one line, giving the story, the verdict (merged, sent
  back or blocked) and the commit.
- **At the end:** what merged, what is blocked and why, and the validation
  evidence. Report a failure with its output.

## Token discipline

- Keep implementer output in files, and read only final messages.
- Review diffs per file, not as one huge dump.
- Write briefs only when the story is next, never all at once.
- For a long run, start a fresh Claude session per wave. The repo, the briefs
  and git hold all the state.
