import json
import subprocess

import pytest
from rn_forge.cli import ExitCode, run
from rn_forge.commons.fs.blocks import ManagedBlock
from rn_forge.tooling.install import ToolHome, doctor

from rn_forge.agentkit import adapters
from rn_forge.agentkit import findings as findings_module
from rn_forge.agentkit.adapters.instructions import BLOCK
from rn_forge.agentkit.main import app
from rn_forge.agentkit.product import PRODUCT


@pytest.fixture
def home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("RNF_HOME", str(home / ".rn-forge"))
    monkeypatch.setattr(adapters, "render", lambda target, agents, sources: [])
    monkeypatch.setattr(
        findings_module.shutil, "which", lambda name: f"/usr/bin/{name}"
    )
    return home


@pytest.fixture
def repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    return repo


def _write(root, path, text):
    file = root / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text)


def _plan_findings(capsys, repo=None):
    args = ["--json", "plan"]
    if repo is not None:
        args.extend(["--scope", "repo", "--repo", str(repo)])
    capsys.readouterr()
    code = run(app, args)
    output = capsys.readouterr().out
    findings = json.loads(output).get("findings", []) if output else []
    return code, [
        finding
        for finding in findings
        if finding["code"].startswith("agentkit.")
        and finding["code"]
        not in {
            "agentkit.agent-missing",
            "agentkit.jq-missing",
            "agentkit.gitleaks-missing",
        }
    ]


@pytest.mark.parametrize(
    ("scope", "path"),
    [("repo", "AGENTS.md"), ("machine", ".claude/CLAUDE.md")],
)
def test_s5_1_2_malformed_markers_are_an_error(home, repo, capsys, scope, path):
    root = repo if scope == "repo" else home
    _write(root, path, "<!-- BEGIN rn-forge agentkit -->\nx\n")

    code, findings = _plan_findings(capsys, repo if scope == "repo" else None)

    assert code != ExitCode.OK
    assert [finding["code"] for finding in findings] == ["agentkit.block-malformed"]
    assert findings[0]["severity"] == "error"
    assert findings[0]["message"].startswith(f"{path}: ")


_DUPLICATE_HEADING = BLOCK.render("## Safety\n\n## Mine\n", "## Safety\n\n- x\n")
_KILN = ManagedBlock("rn-forge kiln", comment="<!--")


@pytest.mark.parametrize(
    ("scope", "path", "content"),
    [
        ("repo", "AGENTS.md", _DUPLICATE_HEADING),
        ("repo", "CLAUDE.md", "@AGENTS.md\n\n" + _DUPLICATE_HEADING),
        ("machine", ".claude/CLAUDE.md", _DUPLICATE_HEADING),
        (
            "repo",
            "AGENTS.md",
            BLOCK.render(_KILN.render("", "## Safety\n"), "## Safety\n"),
        ),
        ("repo", "CLAUDE.md", "# Claude\n\nNotes.\n"),
        ("repo", "AGENTS.md", "Read `CLAUDE.md` now\n"),
    ],
    ids=[
        "repo-agents-body",
        "repo-claude-body",
        "machine-claude-body",
        "kiln-block",
        "missing-import",
        "claude-pointer",
    ],
)
def test_s5_1_2_body_edits_are_silent(home, repo, capsys, scope, path, content):
    root = repo if scope == "repo" else home
    _write(root, path, content)

    code, findings = _plan_findings(capsys, repo if scope == "repo" else None)

    assert code == ExitCode.OK
    assert findings == []


def test_s5_1_2_doctor_is_silent_on_body_edit(home):
    _write(home, ".claude/CLAUDE.md", _DUPLICATE_HEADING)

    found = doctor(PRODUCT, home=ToolHome("agentkit", home / ".rn-forge"))

    assert [
        f for f in found if f.code.startswith(("agentkit.heading", "agentkit.block"))
    ] == []
