import json
import subprocess

import pytest
from rn_forge.cli import ExitCode, run
from rn_forge.commons.fs.state import StateStore
from rn_forge.commons.generation import ArtifactKind, StateEntry

from rn_forge.agentkit.main import app

KILN_AGENTS = (
    "# AGENTS.md\n\nBody text.\n\n"
    "<!-- BEGIN rn-forge kiln -->\n## Repository standard (kiln)\n\n"
    "kiln text.\n<!-- END rn-forge kiln -->\n"
)


@pytest.fixture
def home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("RNF_HOME", str(home / ".rn-forge"))
    return home


@pytest.fixture
def repo(tmp_path):
    repo = tmp_path / "myrepo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "AGENTS.md").write_text(KILN_AGENTS)
    return repo


def _state(repo):
    store = StateStore(repo / ".rn-forge/agentkit/state.json", entry_type=StateEntry)
    return store.load()


def test_s2_2_2_absent_claude_md_is_seeded(home, repo):
    args = ["apply", "--scope", "repo", "--repo", str(repo)]
    assert run(app, args) == ExitCode.OK
    assert (repo / "CLAUDE.md").read_bytes() == b"@AGENTS.md\n"
    entry = _state(repo)["CLAUDE.md"]
    assert entry.kind == ArtifactKind.SEEDED
    assert entry.content_hash is None


def test_s2_2_2_present_claude_md_is_never_read_or_rewritten(home, repo, capsys):
    claude = repo / "CLAUDE.md"
    claude.write_bytes(b"\xff\xfe not utf-8\n")
    args = ["apply", "--scope", "repo", "--repo", str(repo)]
    assert run(app, args) == ExitCode.OK
    assert claude.read_bytes() == b"\xff\xfe not utf-8\n"
    capsys.readouterr()
    assert run(app, ["--json", *args]) == ExitCode.OK
    assert claude.read_bytes() == b"\xff\xfe not utf-8\n"
    changes = json.loads(capsys.readouterr().out)
    actions = {c["path"]: c["action"] for c in changes}
    assert actions["CLAUDE.md"] == "skip"


def test_s2_2_2_seed_survives_a_hand_edit(home, repo):
    args = ["apply", "--scope", "repo", "--repo", str(repo)]
    assert run(app, args) == ExitCode.OK
    (repo / "CLAUDE.md").write_text("@AGENTS.md\n\n## Claude-only\n")
    assert run(app, args) == ExitCode.OK
    assert (repo / "CLAUDE.md").read_text() == "@AGENTS.md\n\n## Claude-only\n"


def test_s2_2_2_remove_keeps_claude_md(home, repo):
    assert run(app, ["apply", "--scope", "repo", "--repo", str(repo)]) == ExitCode.OK
    assert run(app, ["remove", "--scope", "repo", "--repo", str(repo)]) == ExitCode.OK
    assert (repo / "CLAUDE.md").read_text() == "@AGENTS.md\n"
    assert "CLAUDE.md" not in _state(repo)
