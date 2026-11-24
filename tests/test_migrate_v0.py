import json

import pytest
from rn_forge.cli import ExitCode, run
from rn_forge.commons.findings import Severity
from rn_forge.commons.generation import Artifact, ArtifactKind
from rn_forge.tooling.install import ToolHome, doctor

from rn_forge.agentkit import adapters
from rn_forge.agentkit import findings as findings_module
from rn_forge.agentkit.main import app
from rn_forge.agentkit.product import PRODUCT

V0 = rb"""{
  "/abs/home/.claude/CLAUDE.md": {
    "hash": "0c25\u2026",
    "last_applied": "2026-09-04T20:04:33+00:00",
    "path": "/abs/home/.claude/CLAUDE.md",
    "source_layer": "packaged"
  }
}
"""


@pytest.fixture
def home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("RNF_HOME", str(home / ".rn-forge"))
    monkeypatch.setattr(
        adapters,
        "render",
        lambda target, agents, sources: [
            Artifact(".agent/one.md", ArtifactKind.MANAGED, "one\n")
        ],
    )
    return home


@pytest.fixture
def which(monkeypatch):
    missing: set[str] = set()
    monkeypatch.setattr(
        findings_module.shutil,
        "which",
        lambda name: None if name in missing else f"/usr/bin/{name}",
    )
    return missing


@pytest.fixture
def state(home):
    return home / ".rn-forge" / "share" / "agentkit" / "state.json"


def _doctor(home):
    return doctor(PRODUCT, home=ToolHome("agentkit", home / ".rn-forge"))


def _write_v0(state):
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_bytes(V0)


def test_s4_2_1_doctor_reports_v0_install(home, which):
    install = home / ".rn-forge" / "agentkit"
    (install / "v0.5.0").mkdir(parents=True)
    (install / "current").symlink_to("v0.5.0")
    findings = [f for f in _doctor(home) if f.code == "agentkit.v0-install"]
    assert len(findings) == 1
    assert findings[0].severity is Severity.WARNING
    assert "step 2" in findings[0].message


def test_s4_2_1_versions_layout_is_not_v0(home, which):
    (home / ".rn-forge" / "agentkit" / "versions" / "0.1.0").mkdir(parents=True)
    assert all(f.code != "agentkit.v0-install" for f in _doctor(home))


def test_s4_2_1_doctor_reports_v0_state(home, which, state):
    _write_v0(state)
    findings = [f for f in _doctor(home) if f.code == "agentkit.v0-state"]
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert "migrate-v0" in findings[0].message
    assert "step 4" in findings[0].message


def test_s4_2_1_v1_state_is_not_v0(home, which):
    assert run(app, ["apply"]) == ExitCode.OK
    assert all(f.code != "agentkit.v0-state" for f in _doctor(home))


def test_s4_2_1_migrate_renames_and_keeps(home, which, state, capsys):
    _write_v0(state)
    assert run(app, ["migrate-v0"]) == ExitCode.OK
    captured = capsys.readouterr()
    assert not state.exists()
    assert state.with_name("state.v0.json").read_bytes() == V0
    assert "renamed" in captured.out


def test_s4_2_1_migrate_twice_is_a_no_op(home, which, state, capsys):
    _write_v0(state)
    assert run(app, ["migrate-v0"]) == ExitCode.OK
    archive = state.with_name("state.v0.json")
    original = archive.read_bytes()
    capsys.readouterr()
    assert run(app, ["migrate-v0"]) == ExitCode.OK
    assert "nothing to migrate" in capsys.readouterr().out
    assert archive.read_bytes() == original == V0


def test_s4_2_1_migrate_with_no_state_is_a_no_op(home, which, state):
    assert run(app, ["migrate-v0"]) == ExitCode.OK
    assert not state.exists()
    assert not state.with_name("state.v0.json").exists()


def test_s4_2_1_migrate_refuses_when_archive_exists(home, which, state):
    _write_v0(state)
    archive = state.with_name("state.v0.json")
    archive.write_text("different archive")
    assert run(app, ["migrate-v0"]) == 1
    assert state.read_bytes() == V0
    assert archive.read_text() == "different archive"


def test_s4_2_1_migrate_json_output(home, which, state, capsys):
    _write_v0(state)
    assert run(app, ["--json", "migrate-v0"]) == ExitCode.OK
    assert json.loads(capsys.readouterr().out) == {
        "archived": str(state.with_name("state.v0.json"))
    }
