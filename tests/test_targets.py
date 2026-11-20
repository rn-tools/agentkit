from pathlib import Path

import pytest
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.runtime.subprocess import Process

from rn_forge.agentkit.sources import Scope
from rn_forge.agentkit.targets import resolve_target


def test_s1_3_1_repo_scope_uses_the_git_top_level(tmp_path):
    repo = tmp_path / "repo"
    sub = repo / "a" / "b"
    sub.mkdir(parents=True)
    Process.execute("git-init", "git", "init", "-q", cwd=repo)
    target = resolve_target(
        Scope.REPO,
        repo=None,
        cwd=sub,
        home=tmp_path / "home",
        rnf_home=tmp_path / "rnf",
    )
    assert target.root == repo.resolve()
    assert target.state_path == repo.resolve() / ".rn-forge/agentkit/state.json"


def test_s1_3_1_repo_flag_overrides_cwd(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    target = resolve_target(
        Scope.REPO,
        repo=plain,
        cwd=tmp_path,
        home=tmp_path / "home",
        rnf_home=tmp_path / "rnf",
    )
    assert target.root == plain


def test_s1_3_1_repo_scope_outside_git_fails(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(AppException, match="not inside a git repository") as info:
        resolve_target(
            Scope.REPO,
            repo=None,
            cwd=outside,
            home=tmp_path / "home",
            rnf_home=tmp_path / "rnf",
        )
    assert str(outside) in str(info.value)


def test_s1_3_1_machine_target_paths(tmp_path):
    home = tmp_path / "home"
    rnf = tmp_path / "rnf"
    target = resolve_target(
        Scope.MACHINE, repo=None, cwd=tmp_path, home=home, rnf_home=rnf
    )
    work = rnf / "share" / "agentkit"
    assert target.root == home
    assert target.work_dir == work
    assert target.state_path == work / "state.json"
    assert target.backup_dir == work / "backups"
    assert target.staging_dir == work / ".staging"
    assert target.user_overlay == work / "config.toml"
    assert target.repo_overlay == home / ".rn-forge" / "agentkit" / "config.toml"
    assert isinstance(target.root, Path)
