from pathlib import Path

import pytest
from rn_forge.cli import ExitCode, run
from rn_forge.commons.fs.blocks import ManagedBlock

import rn_forge.agentkit
from rn_forge.agentkit import adapters
from rn_forge.agentkit.main import app
from rn_forge.agentkit.sources import Scope, load_sources
from rn_forge.agentkit.targets import Agent, resolve_target

ASSETS_DIR = Path(rn_forge.agentkit.__file__).parent / "assets" / "instructions"
SNAP = Path(__file__).parent / "snapshots" / "instructions"
BLOCK = ManagedBlock("rn-forge agentkit", comment="<!--")
STYLE_TITLE = "# Output Style: Concise"


@pytest.fixture
def home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("RNF_HOME", str(home / ".rn-forge"))
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


def rendered(home):
    target, sources = machine(home)
    artifacts = adapters.render(target, [Agent.CLAUDE, Agent.CODEX], sources)
    return {a.path: a.content for a in artifacts}


def texts():
    return (
        (ASSETS_DIR / "rules.md").read_text(),
        (ASSETS_DIR / "style.md").read_text(),
    )


def test_s2_1_1_rules_once_style_only_for_codex(home):
    rules, style = texts()
    out = rendered(home)
    claude = out[".claude/CLAUDE.md"]
    assert claude.count(rules) == 1
    assert STYLE_TITLE not in claude
    codex = out[".codex/AGENTS.md"]
    assert codex.count(rules) == 1
    assert codex.count(style) == 1
    assert out[".claude/output-styles/concise.md"].count(style) == 1


def test_s2_1_1_rendered_outputs_match_snapshots(home):
    rules, style = texts()
    out = rendered(home)
    for path, name in (
        (".claude/CLAUDE.md", "claude-block.md"),
        (".codex/AGENTS.md", "codex-block.md"),
        (".claude/output-styles/concise.md", "concise.md"),
    ):
        assert out[path] == (SNAP / name).read_text()
    assert out[".codex/AGENTS.md"] == rules + "\n" + style


def test_s2_1_1_block_lands_after_an_existing_body(home):
    path = home / ".claude/CLAUDE.md"
    path.parent.mkdir(parents=True)
    path.write_text("# Mine\n\nKeep me.\n")
    assert run(app, ["apply"]) == ExitCode.OK
    text = path.read_text()
    assert text.startswith("# Mine\n\nKeep me.\n\n<!-- BEGIN rn-forge agentkit -->\n")
    assert BLOCK.remove(text) == "# Mine\n\nKeep me.\n"


def test_s2_1_1_absent_file_holds_only_the_block(home):
    rules, style = texts()
    assert run(app, ["apply"]) == ExitCode.OK
    assert (home / ".codex/AGENTS.md").read_text() == (
        "<!-- BEGIN rn-forge agentkit -->\n"
        + rules
        + "\n"
        + style
        + "<!-- END rn-forge agentkit -->\n"
    )


def test_s2_1_1_block_edit_is_drift_body_edit_is_not(home, capsys):
    assert run(app, ["apply"]) == ExitCode.OK
    path = home / ".claude/CLAUDE.md"
    path.write_text("# Mine\n\n" + path.read_text())
    assert run(app, ["apply"]) == ExitCode.OK
    path.write_text(path.read_text().replace("Bias to action", "Bias"))
    capsys.readouterr()
    assert run(app, ["apply"]) == 1
    captured = capsys.readouterr()
    text = captured.out + captured.err
    assert ".claude/CLAUDE.md" in text
    assert "drift" in text
