import stat

from rn_forge.cli import ExitCode, run

from rn_forge.agentkit.main import app

CLAUDE = (
    "pre-bash-guard",
    "pre-write-protect",
    "session-compact-context",
    "user-prompt-secret-guard",
)
CODEX = ("pre-bash-guard", "pre-write-protect", "user-prompt-secret-guard")


def test_s3_1_1_scripts_install_with_mode_0755(isolated_env):
    _, rnf, _ = isolated_env
    assert run(app, ["apply"]) == ExitCode.OK
    share = rnf / "share" / "agentkit"
    for agent, names in (("claude", CLAUDE), ("codex", CODEX)):
        for name in names:
            path = share / agent / "hooks" / f"{name}.sh"
            assert stat.S_IMODE(path.stat().st_mode) == 0o755
    assert (share / "_common" / "hooks" / "guard-core.sh").exists()


def test_s3_1_1_agent_filter_installs_common_library(isolated_env):
    _, rnf, _ = isolated_env
    assert run(app, ["apply", "--agent", "codex"]) == ExitCode.OK
    share = rnf / "share" / "agentkit"
    assert (share / "_common" / "hooks" / "guard-core.sh").exists()
    for name in CODEX:
        assert (share / "codex" / "hooks" / f"{name}.sh").exists()
    assert not list((share / "claude").glob("hooks/*.sh"))


def test_s3_1_1_rnf_home_outside_home_fails(
    isolated_env, tmp_path, monkeypatch, capsys
):
    elsewhere = tmp_path / "elsewhere"
    monkeypatch.setenv("RNF_HOME", str(elsewhere))
    capsys.readouterr()
    assert run(app, ["apply"]) == 1
    captured = capsys.readouterr()
    assert "RNF_HOME must be under HOME" in captured.out + captured.err
    assert not (elsewhere / "share" / "agentkit" / "state.json").exists()


def test_s3_1_1_scripts_say_agentkit_apply(isolated_env):
    _, rnf, _ = isolated_env
    assert run(app, ["apply"]) == ExitCode.OK
    share = rnf / "share" / "agentkit"
    scripts = list(share.glob("*/hooks/*.sh"))
    assert len(scripts) == 8
    for path in scripts:
        text = path.read_text()
        assert "agentkit global apply" not in text
        if path.name.startswith(("pre-", "user-prompt-")):
            assert "Re-run agentkit apply." in text
