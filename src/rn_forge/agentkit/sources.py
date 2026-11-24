"""Load and merge agentkit's three configuration layers.

Packaged defaults, the user overlay and the repository overlay are deep-merged
in that order of precedence, and the layer that won each key is recorded.
"""

from __future__ import annotations

from enum import StrEnum
from importlib.resources import files
from pathlib import Path
from typing import Any

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import DocumentUtils
from rn_forge.commons.lang.collections import DictUtils, MergeResult

TABLES: tuple[str, ...] = ("claude", "codex", "repo")
AGENTS: tuple[str, ...] = ("claude", "codex")


class Scope(StrEnum):
    """Which overlays apply: machine ignores the repository overlay."""

    MACHINE = "machine"
    REPO = "repo"


class Layer(StrEnum):
    """Layer names, in increasing precedence."""

    PACKAGED = "packaged"
    USER = "user"
    REPO = "repo"


class SourceError(AppException):
    """An overlay file is not shaped as agentkit expects."""


def user_overlay_path(rnf_home: Path) -> Path:
    """Return the user overlay path under *rnf_home*."""
    return rnf_home / "share" / "agentkit" / "config.toml"


def repo_overlay_path(repo_root: Path) -> Path:
    """Return the repository overlay path under *repo_root*."""
    return repo_root / ".rn-forge" / "agentkit" / "config.toml"


def load_packaged() -> dict[str, Any]:
    """Read the packaged defaults, one table per agent."""
    root = files("rn_forge.agentkit")
    return {
        agent: DocumentUtils.read(root.joinpath("defaults", f"{agent}.toml"))
        for agent in AGENTS
    }


def load_overlay(path: Path) -> dict[str, Any]:
    """Read an overlay file; a missing file is an empty layer.

    Raises:
        SourceError: A top-level key is not one of `TABLES`.
    """
    overlay = DocumentUtils.read(path, missing_ok=True)
    for key in overlay:
        if key not in TABLES:
            raise SourceError(
                "{}: unknown top-level table {!r}; expected one of {}",
                path,
                key,
                ", ".join(TABLES),
            )
    return overlay


def load_sources(
    scope: Scope, *, user_overlay: Path, repo_overlay: Path
) -> MergeResult:
    """Merge the layers for *scope*, recording which layer won each key."""
    layers: list[tuple[str, dict[str, Any]]] = [
        (Layer.PACKAGED.value, load_packaged()),
        (Layer.USER.value, load_overlay(user_overlay)),
    ]
    if scope is Scope.REPO:
        layers.append((Layer.REPO.value, load_overlay(repo_overlay)))
    return DictUtils.merge_layers(*layers)
