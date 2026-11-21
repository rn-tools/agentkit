import json
import shutil
import tomllib
from pathlib import Path

import pytest
from rn_forge.cli import ExitCode, run

from rn_forge.agentkit.main import app
from rn_forge.agentkit.sources import user_overlay_path

FIXTURES = Path(__file__).parent / "fixtures" / "settings"
CLAUDE = ".claude/settings.json"
CODEX = ".codex/config.toml"
DENY = [
    "Read(**/.env)",
    "Read(**/.env.*)",
    "Read(**/*.pem)",
    "Read(**/*.key)",
    "Read(**/*.p12)",
    "Read(**/*.pfx)",
    "Read(**/*.gpg)",
    "Read(**/*.asc)",
    "Read(**/id_rsa*)",
    "Read(**/id_ed25519*)",
    "Read(**/credentials)",
    "Read(**/credentials.json)",
    "Read(**/service-account*.json)",
    "Read(**/.netrc)",
    "Read(**/.npmrc)",
    "Read(**/.pypirc)",
    "Read(**/.kube/config)",
    "Read(**/.ssh/**)",
    "Read(**/.aws/**)",
    "Read(**/*.tfstate)",
    "Read(**/*.tfvars)",
]


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Isolate both agent homes and agentkit state."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("RNF_HOME", str(tmp_path / ".rn-forge"))
    return tmp_path


@pytest.fixture
def configured(home):
    """Install the synthetic settings files before the first apply."""
    for relative in (CLAUDE, CODEX):
        path = home / relative
        path.parent.mkdir()
        shutil.copyfile(FIXTURES / path.name, path)
    return home


def test_s1_4_2_claude_owned_keys_only(configured):
    assert run(app, ["apply"]) == ExitCode.OK
    actual = json.loads((configured / CLAUDE).read_text())
    assert "hooks" not in actual
    assert actual["outputStyle"] == "concise"
    expected = json.loads((FIXTURES / "settings.json").read_text())
    expected.update(
        effortLevel="medium",
        outputStyle="concise",
        extraKnownMarketplaces={
            "claude-plugins-official": {
                "source": {
                    "source": "github",
                    "repo": "anthropics/claude-plugins-official",
                }
            }
        },
    )
    expected["permissions"]["deny"] = DENY
    assert actual == expected


def test_s1_4_2_codex_owned_keys_only(configured):
    assert run(app, ["apply"]) == ExitCode.OK
    text = (configured / CODEX).read_text()
    assert "# Example model selection" in text
    assert "# Example project permissions" in text
    actual = tomllib.loads(text)
    assert actual["approval_policy"] == "on-request"
    expected = tomllib.loads((FIXTURES / "config.toml").read_text())
    expected.update(
        approval_policy="on-request",
        features={"hooks": True},
        model_reasoning_effort="medium",
        model_reasoning_summary="concise",
        personality="pragmatic",
        profiles={
            "deep": {"model_reasoning_effort": "high"},
            "trusted": {"approval_policy": "never"},
        },
        sandbox_mode="workspace-write",
        sandbox_workspace_write={"network_access": False},
    )
    assert actual == expected


def test_s1_4_2_first_apply_inserts_without_force(configured, capsys):
    assert run(app, ["--json", "plan"]) == ExitCode.OK
    rows = json.loads(capsys.readouterr().out)["changes"]
    actions = {row["path"]: row["action"] for row in rows}
    assert actions[CLAUDE] == "insert"
    assert actions[CODEX] == "insert"
    assert run(app, ["apply"]) == ExitCode.OK


def test_s1_4_2_overlay_owned_key_is_applied(home):
    overlay = user_overlay_path(home / ".rn-forge")
    overlay.parent.mkdir(parents=True)
    overlay.write_text(
        '[claude]\neffortLevel = "high"\n'
        '[codex.profiles.deep]\nmodel_reasoning_effort = "xhigh"\n'
    )
    assert run(app, ["apply"]) == ExitCode.OK
    assert json.loads((home / CLAUDE).read_text())["effortLevel"] == "high"
    config = tomllib.loads((home / CODEX).read_text())
    assert config["profiles"]["deep"]["model_reasoning_effort"] == "xhigh"


def test_s1_4_2_second_apply_is_unchanged(configured, capsys):
    assert run(app, ["apply"]) == ExitCode.OK
    capsys.readouterr()
    assert run(app, ["--json", "apply"]) == ExitCode.OK
    rows = json.loads(capsys.readouterr().out)
    actions = {row["path"]: row["action"] for row in rows}
    assert actions[CLAUDE] == "unchanged"
    assert actions[CODEX] == "unchanged"


def test_s1_4_2_agent_filter(home):
    assert run(app, ["apply", "--agent", "codex"]) == ExitCode.OK
    assert not (home / CLAUDE).exists()
    assert (home / CODEX).is_file()
