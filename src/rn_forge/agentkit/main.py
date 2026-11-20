"""The console-script entry point.

Kiln renders the `[cli]` and `[lifecycle]` tables into the packaged
`cli.toml`. The entry point handles `--version` and delegates commands to
the app built from that declaration.
"""

from __future__ import annotations

import sys
from importlib.resources import files

from rn_forge.commons import console
from rn_forge.commons.fs.documents import DocumentUtils
from rn_forge.tooling.cli.lifecycle import build_tool_app

from rn_forge.agentkit.product import PRODUCT

DECLARATION = files("rn_forge.agentkit").joinpath("cli.toml")
app = build_tool_app(DocumentUtils.read(DECLARATION))


def main() -> int:
    """Print the package version or run the declared CLI."""
    if sys.argv[1:] == ["--version"]:
        console.print(PRODUCT.version)
        return 0
    return app()
