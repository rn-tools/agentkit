import json
import subprocess

import pytest
from rn_forge.cli import ExitCode, run
from rn_forge.commons.fs.blocks import ManagedBlock
from rn_forge.commons.generation import Artifact, ArtifactKind
from rn_forge.tooling.install import ToolHome, doctor

from rn_forge.agentkit import adapters
from rn_forge.agentkit import findings as findings_module
from rn_forge.agentkit.main import app
from rn_forge.agentkit.product import PRODUCT

ARTIFACTS = [
    Artifact(".agent/one.md", ArtifactKind.MANAGED, "one\n"),
    Artifact(
        ".agent/rules.md",
        ArtifactKind.BLOCK,
        "rule\n",
        ManagedBlock("rn-forge agentkit", comment="<!--"),
    ),
]

PROGRAMS = ("jq", "gitleaks", "claude", "codex")


@pytest.fixture
def home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("RNF_HOME", str(home / ".rn-forge"))
    monkeypatch.setattr(adapters, "render", lambda target, agents, sources: ARTIFACTS)
    return home


@pytest.fixture
def which(monkeypatch):
    """Stub `shutil.which`; the returned set holds the missing programs."""
    missing: set[str] = set()
    monkeypatch.setattr(
        findings_module.shutil,
        "which",
        lambda name: None if name in missing else f"/usr/bin/{name}",
    )
    return missing


def _json(capsys, *args):
    capsys.readouterr()
    code = run(app, ["--json", *args])
    captured = capsys.readouterr()
    return code, captured


@pytest.mark.parametrize("state", ["create", "unchanged", "drift", "missing"])
def test_s1_3_2_plan_matches_apply_across_states(home, which, capsys, state):
    if state != "create":
        assert run(app, ["apply"]) == ExitCode.OK
    if state == "drift":
        (home / ".agent/one.md").write_text("edited\n")
    if state == "missing":
        (home / ".agent/one.md").unlink()
    code, captured = _json(capsys, "plan")
    assert code == ExitCode.OK
    changes = json.loads(captured.out)["changes"]
    assert len({c["path"] for c in changes}) == len(changes)
    actions = {c["path"]: c["action"] for c in changes}
    assert actions[".agent/one.md"] == state
    if state in ("create", "unchanged"):
        code, applied = _json(capsys, "apply", "--dry-run")
        assert code == ExitCode.OK
        assert [c["action"] for c in changes] == [
            c["action"] for c in json.loads(applied.out)
        ]
    else:
        capsys.readouterr()
        assert run(app, ["apply", "--dry-run"]) == 1
        applied = capsys.readouterr()
        assert f".agent/one.md ({state})" in applied.out + applied.err


def test_s1_3_2_error_finding_exits_1_warnings_exit_0(home, which, capsys):
    which.add("jq")
    code, captured = _json(capsys, "plan")
    assert code == 1
    found = {f["code"]: f["severity"] for f in json.loads(captured.out)["findings"]}
    assert found["agentkit.jq-missing"] == "error"
    which.clear()
    which.update({"gitleaks", "codex"})
    code, captured = _json(capsys, "plan")
    assert code == ExitCode.OK
    found = {f["code"]: f["severity"] for f in json.loads(captured.out)["findings"]}
    assert found["agentkit.gitleaks-missing"] == "warning"
    assert found["agentkit.agent-missing"] == "warning"


def test_s1_3_2_state_entry_whose_file_is_gone(home, which, capsys):
    assert run(app, ["apply"]) == ExitCode.OK
    (home / ".agent/one.md").unlink()
    code, captured = _json(capsys, "plan")
    assert code == ExitCode.OK
    findings = json.loads(captured.out)["findings"]
    gone = [f for f in findings if f["code"] == "agentkit.state-file-gone"]
    assert any(".agent/one.md" in f["message"] for f in gone)


def test_s1_3_2_invalid_overlay_is_an_error_with_its_path(home, which, capsys):
    overlay = home / ".rn-forge" / "share" / "agentkit" / "config.toml"
    overlay.parent.mkdir(parents=True)
    overlay.write_text("[claude")
    capsys.readouterr()
    assert run(app, ["plan"]) == 1
    captured = capsys.readouterr()
    text = (captured.out + captured.err).replace("\n", "")
    assert str(overlay) in text
    assert "agentkit.overlay-invalid" in text


def test_s1_3_2_repo_scope_skips_machine_findings(home, which, capsys, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    which.update({"jq", "gitleaks", "claude", "codex"})
    code, captured = _json(capsys, "plan", "--scope", "repo", "--repo", str(repo))
    assert code == ExitCode.OK
    codes = {f["code"] for f in json.loads(captured.out)["findings"]}
    assert not codes & {
        "agentkit.jq-missing",
        "agentkit.gitleaks-missing",
        "agentkit.agent-missing",
    }


def test_s1_3_2_doctor_runs_machine_findings(home, which):
    which.update({"jq", "claude"})
    found = doctor(PRODUCT, home=ToolHome("agentkit", home / ".rn-forge"))
    assert [f.code for f in found].count("agentkit.jq-missing") == 1
    agents = [f for f in found if f.code == "agentkit.agent-missing"]
    assert len(agents) == 1
    assert "claude" in agents[0].message
