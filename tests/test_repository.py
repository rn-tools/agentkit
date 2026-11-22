import json
import subprocess

import pytest
from rn_forge.cli import ExitCode, run
from rn_forge.commons.fs.blocks import ManagedBlock
from rn_forge.commons.fs.state import StateStore
from rn_forge.commons.generation import ArtifactKind, StateEntry

from rn_forge.agentkit.main import app

KILN_AGENTS = (
    "# AGENTS.md\n\nBody text.\n\n"
    "<!-- BEGIN rn-forge kiln -->\n## Repository standard (kiln)\n\n"
    "kiln text.\n<!-- END rn-forge kiln -->\n"
)
M = b"<!-- BEGIN rn-forge agentkit -->\n@AGENTS.md\n<!-- END rn-forge agentkit -->\n"


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


def test_s5_1_1_absent_claude_md_gets_only_the_block(home, repo):
    assert run(app, ["apply", "--scope", "repo", "--repo", str(repo)]) == ExitCode.OK
    assert (repo / "CLAUDE.md").read_bytes() == M
    assert _state(repo)["CLAUDE.md#rn-forge agentkit"].kind == ArtifactKind.BLOCK


def test_s5_1_1_body_is_kept_byte_for_byte(home, repo):
    claude = repo / "CLAUDE.md"
    body = b"# Claude\n\nNotes.\n"
    claude.write_bytes(body)
    args = ["apply", "--scope", "repo", "--repo", str(repo)]

    assert run(app, args) == ExitCode.OK
    assert claude.read_bytes() == body + b"\n" + M
    block = ManagedBlock("rn-forge agentkit", comment="<!--")
    assert block.extract(claude.read_text()) == "@AGENTS.md\n"
    assert run(app, args) == ExitCode.OK
    assert claude.read_bytes() == body + b"\n" + M


def test_s5_1_1_body_with_import_still_gets_block(home, repo):
    claude = repo / "CLAUDE.md"
    body = b"@AGENTS.md\n\n## Claude-only\n"
    claude.write_bytes(body)

    assert run(app, ["apply", "--scope", "repo", "--repo", str(repo)]) == ExitCode.OK
    assert claude.read_bytes() == body + b"\n" + M


def test_s5_1_1_plan_inserts_block_without_conflict(home, repo, capsys):
    (repo / "CLAUDE.md").write_bytes(b"# Claude\n")
    args = ["--json", "plan", "--scope", "repo", "--repo", str(repo)]

    assert run(app, args) == ExitCode.OK
    changes = json.loads(capsys.readouterr().out)["changes"]
    claude = next(row for row in changes if row["path"] == "CLAUDE.md")
    assert {key: claude[key] for key in ("action", "kind")} == {
        "action": "insert",
        "kind": "block",
    }
    assert all(row["action"] != "conflict" for row in changes)


def test_s5_1_1_block_written_without_repo_keys(home, repo):
    assert run(app, ["apply", "--scope", "repo", "--repo", str(repo)]) == ExitCode.OK
    assert (repo / "CLAUDE.md").read_bytes() == M
    assert (repo / "AGENTS.md").read_bytes() == KILN_AGENTS.encode()


def test_s5_1_1_remove_takes_block_keeps_body(home, repo):
    claude = repo / "CLAUDE.md"
    body = b"# Claude\n"
    claude.write_bytes(body)
    scope = ["--scope", "repo", "--repo", str(repo)]

    assert run(app, ["apply", *scope]) == ExitCode.OK
    assert claude.read_bytes() == body + b"\n" + M
    assert run(app, ["remove", *scope]) == ExitCode.OK
    assert claude.read_bytes() == body

    claude.unlink()
    assert run(app, ["apply", *scope]) == ExitCode.OK
    assert run(app, ["remove", *scope]) == ExitCode.OK
