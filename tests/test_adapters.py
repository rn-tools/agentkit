import json
import stat

import pytest
from rn_forge.cli import ExitCode, run
from rn_forge.commons.fs.blocks import ManagedBlock
from rn_forge.commons.fs.state import StateStore
from rn_forge.commons.generation import Artifact, ArtifactKind, StateEntry

from rn_forge.agentkit import adapters, operations
from rn_forge.agentkit.adapters import Adapter, ArtifactSpec
from rn_forge.agentkit.main import app
from rn_forge.agentkit.sources import Scope, load_sources
from rn_forge.agentkit.targets import Agent, resolve_target

BLOCK = ManagedBlock("rn-forge agentkit", comment="<!--")
CLAUDE_SPECS = (
    ArtifactSpec(".fake-claude/one.md", ArtifactKind.MANAGED, "one.md"),
    ArtifactSpec(".fake-claude/seed.md", ArtifactKind.SEEDED, "seed.md"),
    ArtifactSpec(
        ".fake-claude/rules.md",
        ArtifactKind.BLOCK,
        "rules.md.j2",
        template=True,
        block=BLOCK,
    ),
    ArtifactSpec(
        ".fake-claude/hook.sh",
        ArtifactKind.MANAGED,
        "hook.sh",
        executable=True,
    ),
)
CODEX_SPECS = (ArtifactSpec(".fake-codex/one.md", ArtifactKind.MANAGED, "codex.md"),)


@pytest.fixture
def home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("RNF_HOME", str(home / ".rn-forge"))
    return home


@pytest.fixture
def fake(home, tmp_path, monkeypatch):
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "one.md").write_text("one {# kept #}\n")
    (assets / "seed.md").write_text("seed\n")
    (assets / "rules.md.j2").write_text(
        "agent={{ agent }} effort={{ config.effort }}\n"
    )
    (assets / "hook.sh").write_text("#!/bin/sh\necho ${#}\n")
    (assets / "codex.md").write_text("codex\n")
    monkeypatch.setattr(adapters, "ASSETS", assets)
    monkeypatch.setattr(adapters, "COMMON", {})
    monkeypatch.setattr(
        adapters,
        "ADAPTERS",
        {
            Agent.CLAUDE: Adapter(Agent.CLAUDE, {Scope.MACHINE: CLAUDE_SPECS}),
            Agent.CODEX: Adapter(Agent.CODEX, {Scope.MACHINE: CODEX_SPECS}),
        },
    )
    overlay = home / ".rn-forge/share/agentkit/config.toml"
    overlay.parent.mkdir(parents=True)
    overlay.write_text('[claude]\neffort = "high"\n')
    return home


def machine(home):
    target = resolve_target(
        Scope.MACHINE, repo=None, cwd=home, home=home, rnf_home=home / ".rn-forge"
    )
    sources = load_sources(
        Scope.MACHINE,
        user_overlay=target.user_overlay,
        repo_overlay=target.repo_overlay,
    )
    return target, sources


def test_s1_4_1_no_two_artifacts_share_a_destination():
    for scope in Scope:
        paths = [
            spec.path
            for adapter in adapters.ADAPTERS.values()
            for spec in adapter.specs.get(scope, ())
        ]
        paths += [spec.path for spec in adapters.COMMON.get(scope, ())]
        assert len(paths) == len(set(paths))


def test_s1_4_1_render_returns_only_selected_agents(fake, tmp_path):
    target, sources = machine(fake)
    claude = adapters.render(target, [Agent.CLAUDE], sources)
    assert [a.path for a in claude] == [
        ".fake-claude/one.md",
        ".fake-claude/seed.md",
        ".fake-claude/rules.md",
        ".fake-claude/hook.sh",
    ]
    codex = adapters.render(target, [Agent.CODEX], sources)
    assert [a.path for a in codex] == [".fake-codex/one.md"]
    repo = tmp_path / "repo"
    repo.mkdir()
    repo_target = resolve_target(
        Scope.REPO, repo=repo, cwd=repo, home=fake, rnf_home=fake / ".rn-forge"
    )
    assert adapters.render(repo_target, [Agent.CLAUDE, Agent.CODEX], sources) == []


def test_s1_4_1_specs_render_to_commons_artifacts(fake):
    target, sources = machine(fake)
    artifacts = adapters.render(target, [Agent.CLAUDE], sources)
    assert all(isinstance(a, Artifact) for a in artifacts)
    assert [(a.kind, a.content) for a in artifacts] == [
        (ArtifactKind.MANAGED, "one {# kept #}\n"),
        (ArtifactKind.SEEDED, "seed\n"),
        (ArtifactKind.BLOCK, "agent=claude effort=high\n"),
        (ArtifactKind.MANAGED, "#!/bin/sh\necho ${#}\n"),
    ]
    assert artifacts[2].block == BLOCK


def test_s1_4_1_executable_is_0755_after_apply(fake):
    assert run(app, ["apply"]) == ExitCode.OK
    mode = (fake / ".fake-claude/hook.sh").stat().st_mode
    assert stat.S_IMODE(mode) == 0o755


def test_s1_4_1_failing_chmod_rolls_back(fake, monkeypatch):
    def boom(path):
        raise OSError("boom")

    monkeypatch.setattr(operations, "make_executable", boom)
    assert run(app, ["apply"]) == 1
    for name in (
        ".fake-claude/one.md",
        ".fake-claude/seed.md",
        ".fake-claude/rules.md",
        ".fake-claude/hook.sh",
        ".fake-codex/one.md",
    ):
        assert not (fake / name).exists()
    assert not (fake / ".rn-forge/share/agentkit/state.json").exists()


@pytest.mark.parametrize("path", ["../outside.md", "a/../../b", "/etc/passwd", ""])
def test_s1_4_1_escaping_path_is_rejected_at_load(path):
    with pytest.raises(ValueError):
        ArtifactSpec(path, ArtifactKind.MANAGED, "x")


def test_s1_4_1_invalid_specs_are_rejected_at_load():
    with pytest.raises(ValueError):
        ArtifactSpec("a.sh", ArtifactKind.SEEDED, "x", executable=True)
    with pytest.raises(ValueError):
        ArtifactSpec("a.md", ArtifactKind.BLOCK, "x")


def test_s1_4_1_agent_filter_keeps_other_agents_files(fake, capsys):
    assert run(app, ["apply"]) == ExitCode.OK
    assert run(app, ["apply", "--agent", "claude"]) == ExitCode.OK
    assert (fake / ".fake-codex/one.md").exists()
    state = StateStore(
        fake / ".rn-forge/share/agentkit/state.json", entry_type=StateEntry
    ).load()
    assert ".fake-codex/one.md" in state
    capsys.readouterr()
    assert run(app, ["--json", "apply"]) == ExitCode.OK
    items = json.loads(capsys.readouterr().out)
    assert items
    assert all(item["action"] in {"unchanged", "skip"} for item in items)


def test_s1_4_1_agent_filter_keeps_other_agents_blocks(fake):
    assert run(app, ["apply"]) == ExitCode.OK
    assert run(app, ["apply", "--agent", "codex"]) == ExitCode.OK
    assert "agent=claude" in (fake / ".fake-claude/rules.md").read_text()
    state = StateStore(
        fake / ".rn-forge/share/agentkit/state.json", entry_type=StateEntry
    ).load()
    assert ".fake-claude/rules.md#rn-forge agentkit" in state
