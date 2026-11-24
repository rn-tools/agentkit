import json
import tomllib

import pytest
from rn_forge.cli import ExitCode, run
from rn_forge.commons.fs.state import StateStore
from rn_forge.commons.generation import ArtifactKind, StateEntry

from rn_forge.agentkit import adapters
from rn_forge.agentkit.adapters import Adapter, ArtifactSpec
from rn_forge.agentkit.main import app
from rn_forge.agentkit.sources import Scope, load_sources
from rn_forge.agentkit.targets import Agent, resolve_target

CLAUDE = ".fake-claude/settings.json"
CODEX = ".fake-codex/config.toml"
OVERLAY = ".rn-forge/share/agentkit/config.toml"
STATE = ".rn-forge/share/agentkit/state.json"
CONFIG = """[claude]
effortLevel = "high"

[claude.permissions]
deny = ["Read(./.env)", "Read(./secrets/**)"]

[codex]
approval_policy = "never"

[codex.features]
hooks = true
"""
DENY = ["Read(./.env)", "Read(./secrets/**)"]


@pytest.fixture
def home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("RNF_HOME", str(home / ".rn-forge"))
    return home


@pytest.fixture
def fake(home, monkeypatch):
    monkeypatch.setattr(
        "rn_forge.agentkit.sources.load_packaged",
        lambda: {"claude": {}, "codex": {}},
    )
    claude = ArtifactSpec(
        CLAUDE, ArtifactKind.KEYS, "", keys=("effortLevel", "permissions.deny")
    )
    codex = ArtifactSpec(
        CODEX, ArtifactKind.KEYS, "", keys=("approval_policy", "features.hooks")
    )
    monkeypatch.setattr(adapters, "COMMON", {})
    monkeypatch.setattr(
        adapters,
        "ADAPTERS",
        {
            Agent.CLAUDE: Adapter(Agent.CLAUDE, {Scope.MACHINE: (claude,)}),
            Agent.CODEX: Adapter(Agent.CODEX, {Scope.MACHINE: (codex,)}),
        },
    )
    overlay = home / OVERLAY
    overlay.parent.mkdir(parents=True)
    overlay.write_text(CONFIG)
    return home


def plan_actions(capsys):
    capsys.readouterr()
    run(app, ["--json", "plan"])
    rows = json.loads(capsys.readouterr().out)["changes"]
    return {row["path"]: row["action"] for row in rows}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def machine(home):
    target = resolve_target(
        Scope.MACHINE, repo=None, cwd=home, home=home, rnf_home=home / ".rn-forge"
    )
    sources = load_sources(
        Scope.MACHINE,
        user_overlay=target.user_overlay,
        repo_overlay=target.repo_overlay,
    )
    return target, sources


def test_s1_2_2_spec_requires_keys_for_kind_keys():
    with pytest.raises(ValueError):
        ArtifactSpec("a.json", ArtifactKind.KEYS, "")
    with pytest.raises(ValueError):
        ArtifactSpec("a.md", ArtifactKind.MANAGED, "x", keys=("a",))


def test_s1_2_2_insert_over_app_written_file(fake, capsys):
    path = fake / CLAUDE
    original = {
        "model": "opus",
        "permissions": {"allow": ["Bash(ls)"]},
        "env": {"B": "2", "A": "1"},
    }
    write_json(path, original)
    assert plan_actions(capsys)[CLAUDE] == "insert"
    assert run(app, ["apply"]) == ExitCode.OK
    expected = {
        **original,
        "effortLevel": "high",
        "permissions": {"allow": ["Bash(ls)"], "deny": DENY},
    }
    assert path.read_text().rstrip("\n") == json.dumps(
        expected, indent=2, sort_keys=True
    )


def test_s1_2_2_toml_comments_and_unowned_keys_survive(fake):
    path = fake / CODEX
    path.parent.mkdir(parents=True)
    path.write_text(
        '# top comment\nmodel = "o3" # model comment\n\n[projects."/x"]\n# trust comment\ntrust_level = "trusted"\n'
    )
    assert run(app, ["apply"]) == ExitCode.OK
    text = path.read_text()
    assert "# top comment" in text
    assert "# model comment" in text
    assert "# trust comment" in text
    data = tomllib.loads(text)
    assert data["model"] == "o3"
    assert data["projects"] == {"/x": {"trust_level": "trusted"}}
    assert data["approval_policy"] == "never"
    assert data["features"]["hooks"] is True


def test_s1_2_2_unowned_key_added_after_apply_is_unchanged(fake, capsys):
    assert run(app, ["apply"]) == ExitCode.OK
    path = fake / CLAUDE
    data = json.loads(path.read_text())
    data["theme"] = "dark"
    write_json(path, data)
    assert plan_actions(capsys) == {CLAUDE: "unchanged", CODEX: "unchanged"}


def test_s1_2_2_owned_value_changed_on_disk_is_drift(fake, capsys):
    assert run(app, ["apply"]) == ExitCode.OK
    path = fake / CLAUDE
    data = json.loads(path.read_text())
    data["effortLevel"] = "low"
    write_json(path, data)
    edited = path.read_text()
    assert plan_actions(capsys)[CLAUDE] == "drift"
    assert run(app, ["apply"]) == 1
    assert path.read_text() == edited
    assert run(app, ["apply", "--force", CLAUDE]) == ExitCode.OK
    assert json.loads(path.read_text())["effortLevel"] == "high"
    backups = list((fake / ".rn-forge/share/agentkit/backups").glob(f"*/{CLAUDE}"))
    assert len(backups) == 1
    assert backups[0].read_text() == edited


def test_s1_2_2_list_is_compared_whole(fake, capsys):
    assert run(app, ["apply"]) == ExitCode.OK
    path = fake / CLAUDE
    data = json.loads(path.read_text())
    data["permissions"]["deny"].append("Read(./x)")
    write_json(path, data)
    assert plan_actions(capsys)[CLAUDE] == "drift"


def test_s1_2_2_dropped_path_is_removed(fake, monkeypatch):
    path = fake / CLAUDE
    write_json(path, {"permissions": {"allow": ["Bash(ls)"]}})
    assert run(app, ["apply"]) == ExitCode.OK
    spec = ArtifactSpec(CLAUDE, ArtifactKind.KEYS, "", keys=("effortLevel",))
    monkeypatch.setitem(
        adapters.ADAPTERS, Agent.CLAUDE, Adapter(Agent.CLAUDE, {Scope.MACHINE: (spec,)})
    )
    assert run(app, ["apply"]) == ExitCode.OK
    data = json.loads(path.read_text())
    assert data["effortLevel"] == "high"
    assert data["permissions"]["allow"] == ["Bash(ls)"]
    assert "deny" not in data["permissions"]
    state = StateStore(fake / STATE, entry_type=StateEntry).load()
    assert state[CLAUDE].key_paths == ("effortLevel",)


def test_s1_2_2_absent_config_path_is_not_rendered(fake):
    overlay = fake / OVERLAY
    overlay.write_text(CONFIG.split("[codex.features]")[0])
    target, sources = machine(fake)
    artifacts = adapters.render(target, [Agent.CODEX], sources)
    assert len(artifacts) == 1
    assert artifacts[0].keys == {"approval_policy": "never"}
    overlay.write_text(CONFIG.split("[codex]")[0])
    target, sources = machine(fake)
    assert adapters.render(target, [Agent.CODEX], sources) == []


def test_s1_2_2_absent_file_is_created_with_owned_keys_only(fake, capsys):
    assert plan_actions(capsys) == {CLAUDE: "create", CODEX: "create"}
    assert run(app, ["apply"]) == ExitCode.OK
    assert json.loads((fake / CLAUDE).read_text()) == {
        "effortLevel": "high",
        "permissions": {"deny": DENY},
    }
    assert tomllib.loads((fake / CODEX).read_text()) == {
        "approval_policy": "never",
        "features": {"hooks": True},
    }


def test_s1_2_2_remove_keeps_the_file(fake):
    path = fake / CLAUDE
    write_json(path, {"model": "opus"})
    assert run(app, ["apply"]) == ExitCode.OK
    assert run(app, ["remove", "--yes"]) == ExitCode.OK
    assert path.exists()
    assert json.loads(path.read_text()) == {"model": "opus"}


def test_s1_2_2_diff_shows_owned_change(fake, capsys):
    assert run(app, ["apply"]) == ExitCode.OK
    overlay = fake / OVERLAY
    overlay.write_text(CONFIG.replace('effortLevel = "high"', 'effortLevel = "medium"'))
    capsys.readouterr()
    assert run(app, ["diff"]) == ExitCode.OK
    lines = capsys.readouterr().out.splitlines()
    assert any(line.startswith("-") and '"high"' in line for line in lines)
    assert any(line.startswith("+") and '"medium"' in line for line in lines)
