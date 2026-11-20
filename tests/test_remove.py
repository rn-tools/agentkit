import json
import subprocess

import pytest
from rn_forge.cli import ExitCode, run
from rn_forge.commons.fs.blocks import ManagedBlock
from rn_forge.commons.fs.state import StateStore
from rn_forge.commons.generation import Artifact, ArtifactKind, StateEntry

from rn_forge.agentkit import adapters
from rn_forge.agentkit import commands as commands_module
from rn_forge.agentkit.main import app

ARTIFACTS = [
    Artifact(".agent/one.md", ArtifactKind.MANAGED, "one\n"),
    Artifact(
        ".agent/rules.md",
        ArtifactKind.BLOCK,
        "rule\n",
        ManagedBlock("rn-forge agentkit", comment="<!--"),
    ),
]


@pytest.fixture
def home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("RNF_HOME", str(home / ".rn-forge"))
    monkeypatch.setattr(adapters, "render", lambda target, agents, sources: ARTIFACTS)
    (home / ".agent").mkdir()
    (home / ".agent/rules.md").write_text("# Body\n")
    return home


def _share(home):
    return home / ".rn-forge/share/agentkit"


def _confirm(monkeypatch, answer):
    monkeypatch.setattr(commands_module.console, "confirm", lambda *a, **k: answer)


def test_s1_3_3_remove_deletes_managed_and_strips_blocks(home):
    assert run(app, ["apply"]) == ExitCode.OK
    assert run(app, ["remove", "--yes"]) == ExitCode.OK
    assert not (home / ".agent/one.md").exists()
    assert (home / ".agent/rules.md").read_text() == "# Body\n"
    assert not _share(home).exists()


def test_s1_3_3_touched_files_are_backed_up(home, monkeypatch):
    _confirm(monkeypatch, False)
    assert run(app, ["apply"]) == ExitCode.OK
    assert run(app, ["remove"]) == ExitCode.OK
    backups = _share(home) / "backups"
    assert len(list(backups.glob("*/.agent/one.md"))) == 1
    assert len(list(backups.glob("*/.agent/rules.md"))) == 1


def test_s1_3_3_drifted_file_is_left_and_reported(home, monkeypatch, capsys):
    _confirm(monkeypatch, False)
    assert run(app, ["apply"]) == ExitCode.OK
    (home / ".agent/one.md").write_text("edited\n")
    capsys.readouterr()
    assert run(app, ["--json", "remove"]) == ExitCode.OK
    data = json.loads(capsys.readouterr().out)
    assert data["left"] == [".agent/one.md"]
    assert (home / ".agent/one.md").read_text() == "edited\n"
    assert (home / ".agent/rules.md").read_text() == "# Body\n"


def test_s1_3_3_prompt_no_keeps_share_dir(home, monkeypatch):
    _confirm(monkeypatch, False)
    assert run(app, ["apply"]) == ExitCode.OK
    assert run(app, ["remove"]) == ExitCode.OK
    assert _share(home).exists()


def test_s1_3_3_after_remove_nothing_is_recorded(home, monkeypatch):
    assert run(app, ["apply"]) == ExitCode.OK
    assert run(app, ["remove", "--yes"]) == ExitCode.OK
    _confirm(monkeypatch, False)
    assert run(app, ["apply"]) == ExitCode.OK
    assert run(app, ["remove"]) == ExitCode.OK
    store = StateStore(_share(home) / "state.json", entry_type=StateEntry)
    assert store.load() == {}


def test_s1_3_3_repo_scope_has_no_prompt(home, tmp_path, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("prompted")

    monkeypatch.setattr(commands_module.console, "confirm", boom)
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    assert run(app, ["apply", "--scope", "repo", "--repo", str(repo)]) == ExitCode.OK
    assert run(app, ["remove", "--scope", "repo", "--repo", str(repo)]) == ExitCode.OK
    state = repo / ".rn-forge/agentkit/state.json"
    store = StateStore(state, entry_type=StateEntry)
    assert store.load() == {}


def test_s1_3_3_readme_says_remove_before_uninstall():
    from pathlib import Path

    text = (Path(__file__).parent.parent / "README.md").read_text()
    assert "agentkit remove --scope machine" in text
    assert text.index("agentkit remove --scope machine") < text.index(
        "agentkit uninstall"
    )
