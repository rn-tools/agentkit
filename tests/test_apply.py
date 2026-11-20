import hashlib
import json
from pathlib import Path

import pytest
from rn_forge.cli import ExitCode, run
from rn_forge.commons.fs.blocks import ManagedBlock
from rn_forge.commons.generation import Artifact, ArtifactKind

from rn_forge.agentkit import adapters
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
    return home


def tree_hash(path: Path) -> str:
    digest = hashlib.sha256()
    for file in sorted(p for p in path.rglob("*") if p.is_file()):
        digest.update(str(file.relative_to(path)).encode())
        digest.update(file.read_bytes())
    return digest.hexdigest()


def test_s1_3_1_dry_run_and_diff_write_nothing(home):
    before = tree_hash(home)
    assert run(app, ["apply", "--dry-run"]) == ExitCode.OK
    assert run(app, ["diff"]) == ExitCode.OK
    assert tree_hash(home) == before


def test_s1_3_1_drift_blocks_and_writes_nothing(home, capsys):
    assert run(app, ["apply"]) == ExitCode.OK
    (home / ".agent/one.md").write_text("edited\n")
    before = tree_hash(home)
    capsys.readouterr()
    assert run(app, ["apply"]) == 1
    captured = capsys.readouterr()
    text = captured.out + captured.err
    assert ".agent/one.md" in text
    assert "drift" in text
    assert tree_hash(home) == before


def _drift_both(home):
    assert run(app, ["apply"]) == ExitCode.OK
    (home / ".agent/one.md").write_text("edited\n")
    (home / ".agent/rules.md").write_text(
        "<!-- BEGIN rn-forge agentkit -->\nx\n<!-- END rn-forge agentkit -->\n"
    )


def test_s1_3_1_force_approves_only_the_named_path(home, capsys):
    _drift_both(home)
    capsys.readouterr()
    assert run(app, ["apply", "--force", ".agent/one.md"]) == 1
    captured = capsys.readouterr()
    assert ".agent/rules.md" in captured.out + captured.err
    assert (
        run(app, ["apply", "--force", ".agent/one.md", "--force", ".agent/rules.md"])
        == ExitCode.OK
    )
    assert (home / ".agent/one.md").read_text() == "one\n"
    assert "rule\n" in (home / ".agent/rules.md").read_text()


def test_s1_3_1_overwritten_files_are_backed_up_first(home):
    _drift_both(home)
    assert (
        run(app, ["apply", "--force", ".agent/one.md", "--force", ".agent/rules.md"])
        == ExitCode.OK
    )
    backups = list((home / ".rn-forge/share/agentkit/backups").glob("*/.agent/one.md"))
    assert len(backups) == 1
    assert backups[0].read_text() == "edited\n"


def test_s1_3_1_diff_prints_unified_and_json_lists_the_plan(home, capsys):
    assert run(app, ["diff"]) == ExitCode.OK
    assert "+++ .agent/one.md" in capsys.readouterr().out
    assert run(app, ["--json", "diff"]) == ExitCode.OK
    items = json.loads(capsys.readouterr().out)
    assert all(set(item) == {"path", "kind", "action"} for item in items)
    assert {"path": ".agent/one.md", "kind": "managed", "action": "create"} in items


def test_s1_3_1_second_apply_is_all_unchanged(home, capsys):
    assert run(app, ["apply"]) == ExitCode.OK
    capsys.readouterr()
    assert run(app, ["--json", "apply"]) == ExitCode.OK
    items = json.loads(capsys.readouterr().out)
    assert items
    assert all(item["action"] == "unchanged" for item in items)


def test_s1_3_1_machine_state_lives_in_the_share_dir(home):
    assert run(app, ["apply"]) == ExitCode.OK
    assert (home / ".rn-forge/share/agentkit/state.json").is_file()
    assert not (home / ".rn-forge/agentkit").exists()
