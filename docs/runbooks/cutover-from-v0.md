# Cut over from agentkit v0

Use this procedure to move this machine to v1. Start a dedicated subshell with
`bash` in the repository checkout and run every block in it, so an `exit` in a
block leaves only the subshell and not your interactive shell. Steps that need
the backup directory read its path from a file written in step 1. Each step
marked owner confirms needs the owner's check of the paths and evidence before
the command runs.

## 1. Back up

Keep the original paths relative to home so Claude and Codex files with the same
name stay distinct. Stop on a copy error. Use a fresh backup directory so a
second attempt cannot overwrite the original. A path that does not exist is
skipped and reported. The block records the backup directory in
`~/.rn-forge/backup/cutover-v0-current` for later steps.

```bash
unset RNF_HOME
backup="$HOME/.rn-forge/backup/cutover-v0-$(date +%Y%m%d)"
mkdir -p ~/.rn-forge/backup || exit 1
mkdir -m 700 "$backup" || exit 1
printf '%s\n' "$backup" > ~/.rn-forge/backup/cutover-v0-current || exit 1
saved=(
  .claude/CLAUDE.md .claude/settings.json .claude/output-styles
  .claude/skills .claude/hooks
  .codex/AGENTS.md .codex/config.toml .codex/hooks.json .codex/hooks .codex/skills
  .rn-forge/share/agentkit
)
for path in "${saved[@]}"; do
  if [[ ! -e "$HOME/$path" && ! -L "$HOME/$path" ]]; then
    echo "skipped $path (absent)"
    continue
  fi
  mkdir -p "$backup/${path%/*}" || exit 1
  cp -a "$HOME/$path" "$backup/$path" || exit 1
done
ls -la "$backup"
for path in "${saved[@]}"; do
  [[ ! -e "$HOME/$path" && ! -L "$HOME/$path" ]] || ls -ld "$backup/$path"
done
```

Verify that each path not reported as skipped was saved.

## 2. Move the old install aside

Check that the destination is free and that the link points to
`../agentkit/current/bin/agentkit`.

```bash
test ! -e ~/.rn-forge/agentkit-v0 && test ! -L ~/.rn-forge/agentkit-v0 || exit 1
test "$(readlink ~/.rn-forge/bin/agentkit)" = ../agentkit/current/bin/agentkit
```

**Owner confirms** before running.

```bash
mv ~/.rn-forge/agentkit ~/.rn-forge/agentkit-v0
rm ~/.rn-forge/bin/agentkit
ls -ld ~/.rn-forge/agentkit-v0/current
test ! -L ~/.rn-forge/bin/agentkit
```

The old install's `current` link is under `agentkit-v0` and its launcher is
gone.

## 3. Install

Build from this checkout. The installer needs the source distribution with a
single project directory and requires its version alongside the archive.

```bash
env -u VIRTUAL_ENV task build
version=$(env -u VIRTUAL_ENV task version)
.venv/bin/agentkit install --version "$version" --archive "dist/agentkit-${version}.tar.gz"
export PATH="$HOME/.rn-forge/bin:$PATH"
command -v agentkit
~/.rn-forge/bin/agentkit --version
```

Verify that the command resolves to `~/.rn-forge/bin/agentkit` and reports the
checkout's version.

## 4. Run `agentkit migrate-v0`

The first run renames `~/.rn-forge/share/agentkit/state.json` to
`~/.rn-forge/share/agentkit/state.v0.json`, preserving the original bytes. If
both already exist, stop and inspect them.

**Owner confirms** before running.

```bash
backup=$(cat ~/.rn-forge/backup/cutover-v0-current)
agentkit migrate-v0
cmp "$backup/.rn-forge/share/agentkit/state.json" ~/.rn-forge/share/agentkit/state.v0.json
agentkit migrate-v0
agentkit doctor
```

The second run prints `nothing to migrate`. The `agentkit.v0-state` finding
should have cleared.

## 5. `agentkit apply --dry-run`

```bash
agentkit plan
agentkit diff
```

Read every row in `agentkit plan`. It gives the full preview because
`agentkit apply --dry-run` stops on blocking rows. Expect `insert` for new
blocks or keys and `create` for missing files. A `conflict` marks an existing
file for which v1 has no state. On this machine, check the live share-directory
hooks, the Claude output style, the skill files and the Codex hook
configuration.

`agentkit diff` shows text changes for write rows such as `insert`, `create` and
`update`. It omits conflicts. Before proceeding, identify every conflict path in
the plan and verify that step 1 saved a copy of each.

## 6. Approve the adopted files with `--force`

Edit the list below to match **only** the `conflict` rows from step 5. Use exact
paths relative to `$HOME`. Read the write-row diffs and review the complete list
of files that apply will touch.

```bash
backup=$(cat ~/.rn-forge/backup/cutover-v0-current)
conflicts=(
  .codex/hooks.json
  .rn-forge/share/agentkit/_common/hooks/guard-core.sh
  .rn-forge/share/agentkit/claude/hooks/pre-bash-guard.sh
  .rn-forge/share/agentkit/claude/hooks/pre-write-protect.sh
  .rn-forge/share/agentkit/claude/hooks/session-compact-context.sh
  .rn-forge/share/agentkit/claude/hooks/user-prompt-secret-guard.sh
  .rn-forge/share/agentkit/codex/hooks/pre-bash-guard.sh
  .rn-forge/share/agentkit/codex/hooks/pre-write-protect.sh
  .rn-forge/share/agentkit/codex/hooks/user-prompt-secret-guard.sh
  .claude/output-styles/concise.md
  .claude/skills/dev-team-orchestration/SKILL.md
  .claude/skills/sonar-cleanup/SKILL.md
  .codex/skills/dev-team-orchestration/SKILL.md
  .codex/skills/sonar-cleanup/SKILL.md
)
force=()
for path in "${conflicts[@]}"; do
  ls -l "$backup/$path" "$HOME/$path"
  force+=(--force "$path")
done
```

**Owner confirms** before running.

```bash
agentkit apply "${force[@]}"
if ! cmp "$backup/.codex/hooks.json" ~/.codex/hooks.json; then
  cp -a "$backup/.codex/hooks.json" ~/.codex/hooks.json
  exit 1
fi
for path in "${conflicts[@]}"; do
  [[ $path != .codex/hooks.json ]] || continue
  if diff -u "$backup/$path" "$HOME/$path"; then
    continue
  else
    status=$?
  fi
  if [[ $status == 1 ]]; then
    read -r -p "Type expected only if every change to $path is intended: " answer || answer=
    [[ $answer != expected ]] || continue
  fi
  cp -a "$backup/$path" "$HOME/$path"
  exit 1
done
agentkit apply
```

With `RNF_HOME` unset, `~/.codex/hooks.json` must be byte-identical to its
backup to preserve Codex hook trust. A mismatch restores it and stops the
cutover. For every other forced file, inspect the unified diff. An unexpected
difference restores that file and stops the cutover. After all comparisons pass
review, the second apply must report only `unchanged` or `skip`.

After a restore from the backup, agentkit's state records the forced content, so
the next `agentkit plan` shows drift for that file. Use "Rolling back", or fix
the cause, before re-running step 6.

## 7. Trim body text the new blocks duplicate

```bash
agentkit doctor
agentkit plan
```

For each `agentkit.heading-duplicated` warning, find the named heading in
`~/.claude/CLAUDE.md` or `~/.codex/AGENTS.md`. Compare its two occurrences.
Delete the duplicate section from the body, outside the
`BEGIN rn-forge agentkit` and `END rn-forge agentkit` markers. Never edit inside
the markers.

**Owner confirms** before running.

```bash
read -r -p 'Path from the warning, relative to home: ' path
case "$path" in
  .claude/CLAUDE.md|.codex/AGENTS.md) vi "$HOME/$path" ;;
  *) exit 1 ;;
esac
```

Run `agentkit doctor` again. It must exit 0 with no `agentkit.*`
instruction-file warnings.

## 8. Remove the dead leftovers

Inspect the first line of each old Claude hook and search the active settings
for the old directory. Continue only if all five headers identify
`# kiln:claude` and the search returns no matches.

```bash
claude_hooks=(
  ~/.claude/hooks/post-edit-git-stage.sh
  ~/.claude/hooks/pre-bash-guard.sh
  ~/.claude/hooks/pre-write-protect.sh
  ~/.claude/hooks/session-compact-context.sh
  ~/.claude/hooks/user-prompt-secret-guard.sh
)
for path in "${claude_hooks[@]}"; do
  printf '%s ' "$path"
  head -1 "$path"
done
if grep -nF '.claude/hooks/' ~/.claude/settings.json; then exit 1; else test "$?" -eq 1; fi
```

Inspect the two Codex links. Both must target the removed `rnforge-ai-config`
checkout and both targets must be missing.

```bash
codex_links=(~/.codex/hooks/pre-bash-guard.sh ~/.codex/hooks/user-prompt-secret-guard.sh)
ls -l "${codex_links[@]}"
for path in "${codex_links[@]}"; do
  test -L "$path" && test ! -e "$path" || exit 1
done
ls -ld ~/.rn-forge/agentkit-rescue/
```

**Owner confirms** before running.

```bash
for path in "${claude_hooks[@]}" "${codex_links[@]}"; do
  rm -i "$path"
  test ! -e "$path" && test ! -L "$path" || exit 1
done
rm -rI ~/.rn-forge/agentkit-rescue
test ! -e ~/.rn-forge/agentkit-rescue
```

Keep `~/.rn-forge/agentkit-v0/` available for rollback until v1 has run cleanly
for a while. Once the owner accepts the v1 install and the rollback window has
closed, remove the old install.

**Owner confirms** before running.

```bash
rm -rI ~/.rn-forge/agentkit-v0
test ! -e ~/.rn-forge/agentkit-v0
```

## Done when

```bash
agentkit doctor
agentkit apply
```

Record the outcome on
[S4.2.2](../specs/epics/E4-lifecycle-and-cutover/F4.2-machine-cutover.md#s422-runbook)
when doctor exits 0 and apply reports every artifact `unchanged` or, for seeds,
`skip`.

## Rolling back

Roll back while `~/.rn-forge/agentkit-v0/` still holds the old install. Start a
`bash` subshell, read `backup` from the file step 1 wrote, and copy the `saved`
list from step 1 into it. Check every present copy before replacing anything.

```bash
backup=$(cat ~/.rn-forge/backup/cutover-v0-current)
ls -ld "$backup" ~/.rn-forge/agentkit-v0/current
for path in "${saved[@]}"; do
  [[ ! -e "$backup/$path" && ! -L "$backup/$path" ]] || ls -ld "$backup/$path"
done
```

**Owner confirms** before running.

```bash
displaced=$(mktemp -d "$backup/rollback-XXXXXX")
for path in "${saved[@]}"; do
  [[ -e "$backup/$path" || -L "$backup/$path" ]] || continue
  if [[ -e "$HOME/$path" || -L "$HOME/$path" ]]; then
    mkdir -p "$displaced/${path%/*}"
    mv "$HOME/$path" "$displaced/$path"
  fi
  cp -a "$backup/$path" "$HOME/$path"
done
if [[ -d ~/.rn-forge/agentkit ]]; then
  mv ~/.rn-forge/agentkit "$displaced/v1-install"
fi
if [[ -L ~/.rn-forge/bin/agentkit ]]; then
  mv ~/.rn-forge/bin/agentkit "$displaced/v1-launcher"
fi
mv ~/.rn-forge/agentkit-v0 ~/.rn-forge/agentkit
ln -s ../agentkit/current/bin/agentkit ~/.rn-forge/bin/agentkit
ls -l ~/.rn-forge/bin/agentkit
~/.rn-forge/bin/agentkit --version
cmp "$backup/.rn-forge/share/agentkit/state.json" ~/.rn-forge/share/agentkit/state.json
```

Verify the restored launcher reports the v0 version and the restored state
matches the original backup.
