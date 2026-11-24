import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from rn_forge.cli import ExitCode, run

from rn_forge.agentkit.main import app

pytestmark = pytest.mark.skipif(shutil.which("jq") is None, reason="jq is required")


def test_s3_1_1_bash_guard_dialects_and_union_patterns(isolated_env) -> None:
    _, rnf, _ = isolated_env
    assert run(app, ["apply"]) == ExitCode.OK

    for command in ("rm -rf /", 'rm -rf "$HOME"', "psql -c 'TRUNCATE;'"):
        payload = {"tool_input": {"command": command}}
        claude = _run(rnf, "claude", "pre-bash-guard.sh", payload)
        codex = _run(rnf, "codex", "pre-bash-guard.sh", payload)
        assert claude.returncode == 2
        assert "BLOCKED [pre-bash-guard]" in claude.stderr
        assert codex.returncode == 0
        assert json.loads(codex.stdout)["decision"] == "block"

    benign = {"tool_input": {"command": "printf hello"}}
    for agent in ("claude", "codex"):
        result = _run(rnf, agent, "pre-bash-guard.sh", benign)
        assert result.returncode == 0
        assert not result.stdout
        assert not result.stderr


@pytest.mark.parametrize(
    ("command", "blocked"),
    [
        ("git push --force origin feature", True),
        ("git push -f origin feature", True),
        ("git push --force-with-lease origin feature", False),
        ("git push origin main --force-with-lease", True),
        ("git push -u origin feature", False),
        ("git push origin HEAD", True),
        ("git push origin main --force", True),
        ("git push origin feature", False),
    ],
)
def test_s3_1_1_git_push_guard_parses_options_and_refs(
    isolated_env, command: str, blocked: bool
) -> None:
    _, rnf, repo = isolated_env
    subprocess.run(
        ["git", "-C", repo, "init", "-b", "main"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert run(app, ["apply"]) == ExitCode.OK
    payload = {"tool_input": {"command": command}}

    claude = _run(rnf, "claude", "pre-bash-guard.sh", payload, cwd=repo)
    codex = _run(rnf, "codex", "pre-bash-guard.sh", payload, cwd=repo)

    assert (claude.returncode == 2) is blocked
    assert bool(codex.stdout) is blocked
    if blocked:
        assert json.loads(codex.stdout)["decision"] == "block"


@pytest.mark.parametrize(
    "variable", ["AGENTKIT_PROTECTED_BRANCHES", "CLAUDE_PROTECTED_BRANCHES"]
)
def test_s3_1_1_protected_branch_environment_variable_and_legacy_fallback(
    isolated_env, variable: str
) -> None:
    _, rnf, repo = isolated_env
    assert run(app, ["apply"]) == ExitCode.OK
    env = os.environ.copy()
    env.pop("AGENTKIT_PROTECTED_BRANCHES", None)
    env.pop("CLAUDE_PROTECTED_BRANCHES", None)
    env[variable] = "release"
    payload = {"tool_input": {"command": "git push origin release"}}

    claude = _run(rnf, "claude", "pre-bash-guard.sh", payload, cwd=repo, env=env)
    codex = _run(rnf, "codex", "pre-bash-guard.sh", payload, cwd=repo, env=env)

    assert claude.returncode == 2
    assert json.loads(codex.stdout)["decision"] == "block"


def test_s3_1_1_truncate_file_utility_is_not_treated_as_sql(isolated_env) -> None:
    _, rnf, repo = isolated_env
    assert run(app, ["apply"]) == ExitCode.OK
    payload = {"tool_input": {"command": "truncate -s 0 app.log"}}

    for agent in ("claude", "codex"):
        result = _run(rnf, agent, "pre-bash-guard.sh", payload, cwd=repo)
        assert result.returncode == 0
        assert not result.stdout
        assert not result.stderr


@pytest.mark.parametrize(
    ("path", "blocked"),
    [
        (".env", True),
        ("config/.env.local", True),
        ("keys/id_ed25519", True),
        ("certs/server.pem", True),
        ("certs/server.key", True),
        ("certs/store.p12", True),
        ("keys/release.asc", True),
        ("cloud/credentials.json", True),
        ("cloud/service-account-prod.json", True),
        ("home/.kube/config", True),
        (".npmrc", True),
        (".pypirc", True),
        (".netrc", True),
        ("config.secrets/value", True),
        ("infra/prod.tfvars", True),
        ("infra/prod.tfstate", True),
        (".git/config", True),
        ("src/settings.py", False),
    ],
)
def test_s3_1_1_write_guard_dialects_share_sensitive_path_rules(
    isolated_env, path: str, blocked: bool
) -> None:
    _, rnf, repo = isolated_env
    assert run(app, ["apply"]) == ExitCode.OK
    payload = {"tool_input": {"file_path": path}}

    claude = _run(rnf, "claude", "pre-write-protect.sh", payload, cwd=repo)
    codex = _run(rnf, "codex", "pre-write-protect.sh", payload, cwd=repo)

    assert (claude.returncode == 2) is blocked
    assert bool(codex.stdout) is blocked
    if blocked:
        assert json.loads(codex.stdout)["decision"] == "block"


@pytest.mark.parametrize(
    "token",
    [
        "sk-abcdefghijklmnop1234",
        "ghp_abcdefghijklmnopqrstuvwxyz",
        "xoxb-abcdefghijklmnop",
    ],
)
def test_s3_1_1_prompt_secret_guard_dialects_and_union_patterns(
    isolated_env, token: str
) -> None:
    _, rnf, _ = isolated_env
    assert run(app, ["apply"]) == ExitCode.OK
    payload = {"prompt": f"please use {token}"}

    claude = _run(rnf, "claude", "user-prompt-secret-guard.sh", payload)
    codex = _run(rnf, "codex", "user-prompt-secret-guard.sh", payload)

    assert claude.returncode == 2
    assert "BLOCKED [user-prompt-secret-guard]" in claude.stderr
    assert codex.returncode == 0
    assert json.loads(codex.stdout)["decision"] == "block"


def test_s3_1_1_prompt_secret_guard_regex_fallback(
    isolated_env, tmp_path: Path
) -> None:
    _, rnf, repo = isolated_env
    assert run(app, ["apply"]) == ExitCode.OK
    env = os.environ.copy()
    env["PATH"] = _path_without_gitleaks(tmp_path)
    payload = {"prompt": "please use sk-abcdefghijklmnop1234"}

    claude = _run(
        rnf, "claude", "user-prompt-secret-guard.sh", payload, cwd=repo, env=env
    )
    codex = _run(
        rnf, "codex", "user-prompt-secret-guard.sh", payload, cwd=repo, env=env
    )

    assert claude.returncode == 2
    assert json.loads(codex.stdout)["decision"] == "block"


def test_s3_1_1_missing_jq_uses_event_specific_fail_modes(
    isolated_env, tmp_path: Path
) -> None:
    _, rnf, repo = isolated_env
    assert run(app, ["apply"]) == ExitCode.OK
    env = os.environ.copy()
    env["PATH"] = _tool_path(tmp_path, ("bash",))

    claude_prompt = _run(
        rnf,
        "claude",
        "user-prompt-secret-guard.sh",
        {"prompt": "hello"},
        cwd=repo,
        env=env,
    )
    codex_prompt = _run(
        rnf,
        "codex",
        "user-prompt-secret-guard.sh",
        {"prompt": "hello"},
        cwd=repo,
        env=env,
    )
    claude_bash = _run(
        rnf,
        "claude",
        "pre-bash-guard.sh",
        {"tool_input": {"command": "printf hello"}},
        cwd=repo,
        env=env,
    )
    codex_bash = _run(
        rnf,
        "codex",
        "pre-bash-guard.sh",
        {"tool_input": {"command": "printf hello"}},
        cwd=repo,
        env=env,
    )
    claude_write = _run(
        rnf,
        "claude",
        "pre-write-protect.sh",
        {"tool_input": {"file_path": ".env"}},
        cwd=repo,
        env=env,
    )
    codex_write = _run(
        rnf,
        "codex",
        "pre-write-protect.sh",
        {"tool_input": {"file_path": ".env"}},
        cwd=repo,
        env=env,
    )

    assert claude_prompt.returncode == 1
    assert "prompt secret scan skipped" in claude_prompt.stderr
    assert codex_prompt.returncode == 0
    assert not codex_prompt.stdout
    assert "prompt secret scan skipped" in codex_prompt.stderr
    assert claude_bash.returncode == 2
    assert json.loads(codex_bash.stdout)["decision"] == "block"
    assert claude_write.returncode == 2
    assert json.loads(codex_write.stdout)["decision"] == "block"


@pytest.mark.parametrize(
    ("agent", "script"),
    [
        ("claude", "pre-bash-guard.sh"),
        ("claude", "user-prompt-secret-guard.sh"),
        ("claude", "pre-write-protect.sh"),
        ("codex", "pre-bash-guard.sh"),
        ("codex", "user-prompt-secret-guard.sh"),
        ("codex", "pre-write-protect.sh"),
    ],
)
def test_s3_1_1_missing_guard_library_has_clear_failure(
    isolated_env, agent: str, script: str
) -> None:
    _, rnf, repo = isolated_env
    assert run(app, ["apply"]) == ExitCode.OK
    (rnf / "share/agentkit/_common/hooks/guard-core.sh").unlink()
    payload = (
        {"prompt": "hello"}
        if script.startswith("user-prompt")
        else {
            "tool_input": (
                {"file_path": "src/app.py"}
                if script.startswith("pre-write")
                else {"command": "printf hello"}
            )
        }
    )

    result = _run(rnf, agent, script, payload, cwd=repo)

    assert result.returncode == 2
    assert "guard library missing" in result.stderr


def test_s3_1_1_prompt_secret_guard_keeps_regex_coverage_with_gitleaks(
    isolated_env, tmp_path: Path
) -> None:
    _, rnf, repo = isolated_env
    assert run(app, ["apply"]) == ExitCode.OK
    env = os.environ.copy()
    env["PATH"] = _fake_gitleaks_path(tmp_path, output="no leaks found", exit_code=0)
    payload = {"prompt": "AWS key: AKIAIOSFODNN7EXAMPLE"}

    claude = _run(
        rnf, "claude", "user-prompt-secret-guard.sh", payload, cwd=repo, env=env
    )
    codex = _run(
        rnf, "codex", "user-prompt-secret-guard.sh", payload, cwd=repo, env=env
    )

    assert claude.returncode == 2
    assert "AWS access key" in claude.stderr
    assert json.loads(codex.stdout)["decision"] == "block"
    assert "AWS access key" in json.loads(codex.stdout)["reason"]


@pytest.mark.skipif(shutil.which("gitleaks") is None, reason="gitleaks not installed")
def test_s3_1_1_prompt_secret_guard_reports_gitleaks_detection(isolated_env) -> None:
    _, rnf, repo = isolated_env
    assert run(app, ["apply"]) == ExitCode.OK
    payload = {"prompt": "use ghp_016C7e42F292c6912E7710c838347Ae178B4a"}

    result = _run(rnf, "claude", "user-prompt-secret-guard.sh", payload, cwd=repo)

    assert result.returncode == 2
    assert "secret detected by gitleaks" in result.stderr


def test_s3_1_1_prompt_secret_guard_reports_gitleaks_execution_error(
    isolated_env, tmp_path: Path
) -> None:
    _, rnf, repo = isolated_env
    assert run(app, ["apply"]) == ExitCode.OK
    env = os.environ.copy()
    env["PATH"] = _fake_gitleaks_path(
        tmp_path, output="fatal: invalid configuration", exit_code=1
    )

    result = _run(
        rnf,
        "claude",
        "user-prompt-secret-guard.sh",
        {"prompt": "hello"},
        cwd=repo,
        env=env,
    )

    assert result.returncode == 2
    assert "gitleaks could not run" in result.stderr
    assert "secret detected by gitleaks" not in result.stderr


def _run_raw(
    rnf,
    agent: str,
    script: str,
    payload: str,
) -> subprocess.CompletedProcess:
    """Run a hook with a literal stdin payload, valid JSON or not."""
    path = rnf / "share" / "agentkit" / agent / "hooks" / script
    return subprocess.run(
        [path],
        input=payload,
        text=True,
        capture_output=True,
        check=False,
    )


def _run(
    rnf,
    agent: str,
    script: str,
    payload: dict,
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    path = rnf / "share" / "agentkit" / agent / "hooks" / script
    return subprocess.run(
        [path],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        cwd=cwd,
        env=env,
    )


def _path_without_gitleaks(tmp_path: Path) -> str:
    return _tool_path(tmp_path, ("bash", "cat", "dirname", "grep", "jq"))


def _fake_gitleaks_path(tmp_path: Path, *, output: str, exit_code: int) -> str:
    bin_dir = Path(_path_without_gitleaks(tmp_path))
    script = f"#!/bin/sh\nprintf '%s\\n' '{output}' >&2\nexit {exit_code}\n"
    path = bin_dir / "gitleaks"
    path.write_text(script)
    path.chmod(0o755)
    return str(bin_dir)


def _tool_path(tmp_path: Path, names: tuple[str, ...]) -> str:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    for name in names:
        source = shutil.which(name)
        assert source is not None
        (bin_dir / name).symlink_to(source)
    return str(bin_dir)


@pytest.mark.parametrize(
    "command",
    [
        "rm -r -f /",
        "rm -f -r /",
        "rm --recursive --force /",
        "rm -r --force /",
        "rm -v -rf /",
        "rm -Rf /",
        "rm -r -f ~",
        "/bin/rm -rf /",
        "command rm -rf /",
        "git -C . push --force",
        "git --git-dir=/tmp/x push -f",
    ],
)
def test_s3_1_1_guard_covers_equivalent_destructive_spellings(
    isolated_env, command
) -> None:
    """Separated flags, long flags, and Git global options are not a bypass."""
    _, rnf, _ = isolated_env
    assert run(app, ["apply"]) == ExitCode.OK

    payload = {"tool_input": {"command": command}}
    assert _run(rnf, "claude", "pre-bash-guard.sh", payload).returncode == 2
    codex = _run(rnf, "codex", "pre-bash-guard.sh", payload)
    assert json.loads(codex.stdout)["decision"] == "block"


@pytest.mark.parametrize(
    "command",
    [
        "rm -rf /tmp/scratch",
        "rm -f notes.txt",
        "rm -r build",
        "git push origin feature",
    ],
)
def test_s3_1_1_guard_still_allows_ordinary_commands(isolated_env, command) -> None:
    _, rnf, repo = isolated_env
    assert run(app, ["apply"]) == ExitCode.OK
    subprocess.run(
        ["git", "-C", repo, "init", "-b", "feature"],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = {"tool_input": {"command": command}}
    assert _run(rnf, "claude", "pre-bash-guard.sh", payload).returncode == 0


@pytest.mark.parametrize(
    "payload",
    [
        "",
        "not json at all",
        '{"tool_input": {"command": ',
        '{"tool_input": {"command": 123}}',
        '{"tool_input": {"command": ["rm", "-rf", "/"]}}',
    ],
)
def test_s3_1_1_command_guard_fails_closed_on_unusable_events(
    isolated_env, payload
) -> None:
    """A guard that cannot classify its input must block, not allow."""
    _, rnf, _ = isolated_env
    assert run(app, ["apply"]) == ExitCode.OK

    claude = _run_raw(rnf, "claude", "pre-bash-guard.sh", payload)
    assert claude.returncode == 2
    assert "BLOCKED [pre-bash-guard]" in claude.stderr

    codex = _run_raw(rnf, "codex", "pre-bash-guard.sh", payload)
    assert json.loads(codex.stdout)["decision"] == "block"


@pytest.mark.parametrize(
    "payload",
    ["", "not json at all", '{"tool_input": {"file_path": 123}}'],
)
def test_s3_1_1_write_guard_fails_closed_on_unusable_events(
    isolated_env, payload
) -> None:
    _, rnf, _ = isolated_env
    assert run(app, ["apply"]) == ExitCode.OK

    assert _run_raw(rnf, "claude", "pre-write-protect.sh", payload).returncode == 2
    codex = _run_raw(rnf, "codex", "pre-write-protect.sh", payload)
    assert json.loads(codex.stdout)["decision"] == "block"


def test_s3_1_1_write_guard_allows_events_without_a_path(isolated_env) -> None:
    """An absent path is a well-formed event, not an unusable one."""
    _, rnf, _ = isolated_env
    assert run(app, ["apply"]) == ExitCode.OK

    result = _run(rnf, "claude", "pre-write-protect.sh", {"tool_input": {}})
    assert result.returncode == 0


def test_s3_1_1_prompt_guard_warns_rather_than_blocking_on_bad_events(
    isolated_env,
) -> None:
    """Documented asymmetry: a malformed prompt event enables no destructive act."""
    _, rnf, _ = isolated_env
    assert run(app, ["apply"]) == ExitCode.OK

    claude = _run_raw(rnf, "claude", "user-prompt-secret-guard.sh", "not json")
    assert claude.returncode == 1
    assert "WARNING [user-prompt-secret-guard]" in claude.stderr

    codex = _run_raw(rnf, "codex", "user-prompt-secret-guard.sh", "not json")
    assert codex.returncode == 0
    assert not codex.stdout
