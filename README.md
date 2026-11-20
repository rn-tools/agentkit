# agentkit

What this repository is, in a paragraph.

## Working here

- Run everything through `task`. `task validate` is the gate.
- A file whose first line says it was generated is owned by kiln: edit
  `.rn-forge/kiln/config.toml` and run `task kiln:apply`, never the file. The
  standard is [.rn-forge/kiln/standard.md](.rn-forge/kiln/standard.md).

## Uninstall

Run `agentkit remove --scope machine`, and `agentkit remove --scope repo` in
each repository that used agentkit, before the lifecycle `agentkit uninstall`.
`uninstall` alone leaves the configuration agentkit wrote.

## Conventions

- Python 3.14, `src/` layout, pyright strict, ruff for lint and format.
