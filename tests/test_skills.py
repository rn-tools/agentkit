from pathlib import Path

import pytest
from rn_forge.cli import run
from rn_forge.commons.fs.state import StateStore
from rn_forge.commons.generation import StateEntry

from rn_forge.agentkit.main import app

SNAP = Path(__file__).parent / "snapshots" / "skills"
NAMES = ("dev-team-orchestration", "sonar-cleanup")


@pytest.fixture
def home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("RNF_HOME", str(home / ".rn-forge"))
    return home


def overlay(home, text):
    path = home / ".rn-forge/share/agentkit/config.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_s3_2_1_claude_copies_match_snapshots(home):
    assert run(app, ["apply"]) == 0
    for name in NAMES:
        installed = home / ".claude/skills" / name / "SKILL.md"
        assert installed.read_bytes() == (SNAP / name / "SKILL.md").read_bytes()


def test_s3_2_1_codex_copies_have_codex_front_matter(home):
    assert run(app, ["apply"]) == 0
    for name in NAMES:
        text = (home / ".codex/skills" / name / "SKILL.md").read_text()
        assert text.startswith("---\n")
        front = text.split("---\n")[1]
        keys = [line.split(":", 1)[0] for line in front.splitlines() if line]
        assert sorted(keys) == ["description", "name"]
        assert f"name: {name}" in front
        assert "allowed-tools" not in text
        assert text == (home / ".claude/skills" / name / "SKILL.md").read_text()


def test_s3_2_1_disabled_skill_is_removed_on_apply(home):
    assert run(app, ["apply"]) == 0
    overlay(home, '[codex]\nskills.disabled = ["sonar-cleanup"]\n')
    assert run(app, ["apply"]) == 0
    assert not (home / ".codex/skills/sonar-cleanup/SKILL.md").exists()
    assert (home / ".codex/skills/dev-team-orchestration/SKILL.md").exists()
    assert (home / ".claude/skills/sonar-cleanup/SKILL.md").exists()
    state = StateStore(
        home / ".rn-forge/share/agentkit/state.json", entry_type=StateEntry
    ).load()
    assert ".codex/skills/sonar-cleanup/SKILL.md" not in state


def test_s3_2_1_disabled_must_be_a_list(home, capsys):
    overlay(home, '[codex]\nskills.disabled = "sonar-cleanup"\n')
    assert run(app, ["apply"]) == 1
    captured = capsys.readouterr()
    assert "skills.disabled" in captured.out + captured.err
