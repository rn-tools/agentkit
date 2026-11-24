import json
import stat
from pathlib import Path

import pytest
from rn_forge.cli import ExitCode, run

from rn_forge.agentkit.main import app

SNAPSHOT = Path(__file__).parent / "snapshots/hooks/codex-hooks.json"
CLAUDE = ".claude/settings.json"
CODEX = ".codex/hooks.json"


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Isolate agent homes and state."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("RNF_HOME", raising=False)
    return tmp_path


def _commands(registrations):
    return [
        hook["command"]
        for registration in registrations
        for hook in registration["hooks"]
    ]


def test_s3_1_2_rnf_home_set_prefixes_every_command(home, monkeypatch):
    rnf_home = home / "custom-rnf"
    monkeypatch.setenv("RNF_HOME", str(rnf_home))
    assert run(app, ["apply"]) == ExitCode.OK
    prefix = str(rnf_home / "share/agentkit") + "/"
    codex_hooks = json.loads((home / CODEX).read_text())["hooks"]
    claude_hooks = json.loads((home / CLAUDE).read_text())["hooks"]
    all_commands = [
        command
        for registrations in (*codex_hooks.values(), *claude_hooks.values())
        for command in _commands(registrations)
    ]
    assert len(all_commands) == 7
    for command in all_commands:
        assert command.startswith(prefix)
        path = Path(command)
        assert path.is_file()
        assert stat.S_IMODE(path.stat().st_mode) == 0o755


def test_s3_1_2_rnf_home_unset_codex_is_byte_identical(home):
    assert run(app, ["apply"]) == ExitCode.OK
    assert (home / CODEX).read_bytes() == SNAPSHOT.read_bytes()


def test_s3_1_2_empty_rnf_home_is_unset(home, monkeypatch):
    monkeypatch.setenv("RNF_HOME", "")
    assert run(app, ["apply"]) == ExitCode.OK
    assert (home / CODEX).read_bytes() == SNAPSHOT.read_bytes()


def test_s3_1_2_claude_registrations(home):
    assert run(app, ["apply"]) == ExitCode.OK
    hooks = json.loads((home / CLAUDE).read_text())["hooks"]
    assert set(hooks) == {"PreToolUse", "SessionStart", "UserPromptSubmit"}
    assert [item["matcher"] for item in hooks["PreToolUse"]] == [
        "Bash",
        "Write|Edit|MultiEdit|NotebookEdit",
    ]
    assert [item["matcher"] for item in hooks["SessionStart"]] == ["compact"]
    prefix = "$HOME/.rn-forge/share/agentkit/claude/hooks/"
    assert {event: _commands(entries) for event, entries in hooks.items()} == {
        "UserPromptSubmit": [prefix + "user-prompt-secret-guard.sh"],
        "PreToolUse": [prefix + "pre-bash-guard.sh", prefix + "pre-write-protect.sh"],
        "SessionStart": [prefix + "session-compact-context.sh"],
    }


def test_s3_1_2_unowned_settings_keys_survive(home):
    settings = home / CLAUDE
    settings.parent.mkdir(parents=True)
    settings.write_text(json.dumps({"model": "x", "env": {"A": "1"}}))
    assert run(app, ["apply"]) == ExitCode.OK
    actual = json.loads(settings.read_text())
    assert actual["model"] == "x"
    assert actual["env"] == {"A": "1"}
    assert "hooks" in actual


def test_s3_1_2_second_apply_is_unchanged(home, capsys):
    assert run(app, ["apply"]) == ExitCode.OK
    capsys.readouterr()
    assert run(app, ["--json", "apply"]) == ExitCode.OK
    rows = json.loads(capsys.readouterr().out)
    actions = {row["path"]: row["action"] for row in rows}
    assert actions[CLAUDE] == "unchanged"
    assert actions[CODEX] == "unchanged"
