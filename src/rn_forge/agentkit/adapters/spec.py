"""The data an adapter is made of: artifact specs per scope."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath

from rn_forge.commons.fs.blocks import ManagedBlock
from rn_forge.commons.generation import ArtifactKind

from rn_forge.agentkit.sources import Scope
from rn_forge.agentkit.targets import Agent


@dataclass(frozen=True, slots=True)
class ArtifactSpec:
    """One artifact an adapter writes: where, what kind, and its packaged source.

    Args:
        path: POSIX path relative to the scope root.
        kind: How the artifact is written.
        source: Packaged asset path, relative to the assets directory.
        template: Render *source* through the template engine instead of
            copying it verbatim.
        block: The managed block, for ``ArtifactKind.BLOCK`` only.
        executable: Make the file mode 0755 after apply; managed files only.
        skill: The skill name, if this artifact installs a skill; the overlay's
            ``skills.disabled`` can then turn it off.

    Raises:
        ValueError: *path* is empty or leaves the scope root, *block* does not
            match *kind*, or *executable* is set on a non-managed artifact.
    """

    path: str
    kind: ArtifactKind
    source: str
    template: bool = False
    block: ManagedBlock | None = None
    executable: bool = False
    skill: str | None = None

    def __post_init__(self) -> None:
        """Reject a spec that cannot be rendered safely."""
        pure = PurePosixPath(self.path)
        if not self.path or pure.is_absolute() or ".." in pure.parts:
            raise ValueError(
                f"artifact path {self.path!r} must stay inside the scope root"
            )
        if (self.kind is ArtifactKind.BLOCK) != (self.block is not None):
            raise ValueError(
                f"artifact {self.path!r}: a block is required for, and only for, "
                "kind 'block'"
            )
        if self.executable and self.kind is not ArtifactKind.MANAGED:
            raise ValueError(
                f"artifact {self.path!r}: only managed artifacts can be executable"
            )


@dataclass(frozen=True, slots=True)
class Adapter:
    """An agent and the artifact specs it declares per scope."""

    agent: Agent
    specs: Mapping[Scope, tuple[ArtifactSpec, ...]]
