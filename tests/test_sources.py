from pathlib import Path

import pytest

from rn_forge.agentkit import sources
from rn_forge.agentkit.sources import (
    Scope,
    SourceError,
    load_packaged,
    load_sources,
    repo_overlay_path,
    user_overlay_path,
)


def _paths(tmp_path: Path) -> tuple[Path, Path]:
    return tmp_path / "user.toml", tmp_path / "repo.toml"


def test_s1_1_1_repo_layer_wins_with_provenance(tmp_path, monkeypatch):
    monkeypatch.setattr(
        sources, "load_packaged", lambda: {"claude": {"effortLevel": "low"}}
    )
    user, repo = _paths(tmp_path)
    user.write_text('[claude]\neffortLevel = "medium"\n')
    repo.write_text('[claude]\neffortLevel = "high"\n')
    result = load_sources(Scope.REPO, user_overlay=user, repo_overlay=repo)
    assert result.config["claude"]["effortLevel"] == "high"
    assert result.provenance["claude.effortLevel"] == "repo"


def test_s1_1_1_user_list_replaces_packaged_list(tmp_path, monkeypatch):
    monkeypatch.setattr(
        sources,
        "load_packaged",
        lambda: {"claude": {"permissions": {"deny": ["a", "b"]}}},
    )
    user, repo = _paths(tmp_path)
    user.write_text('[claude.permissions]\ndeny = ["c"]\n')
    result = load_sources(Scope.REPO, user_overlay=user, repo_overlay=repo)
    assert result.config["claude"]["permissions"]["deny"] == ["c"]
    assert result.provenance["claude.permissions.deny"] == "user"


def test_s1_1_1_nested_tables_merge(tmp_path, monkeypatch):
    monkeypatch.setattr(sources, "load_packaged", lambda: {"claude": {"a": {"b": 1}}})
    user, repo = _paths(tmp_path)
    user.write_text("[claude.a]\nc = 2\n")
    result = load_sources(Scope.REPO, user_overlay=user, repo_overlay=repo)
    assert result.config["claude"]["a"] == {"b": 1, "c": 2}
    assert result.provenance["claude.a.b"] == "packaged"
    assert result.provenance["claude.a.c"] == "user"


def test_s1_1_1_absent_overlays_are_empty_layers(tmp_path, monkeypatch):
    packaged = {"claude": {"a": 1}, "codex": {"b": 2}}
    monkeypatch.setattr(sources, "load_packaged", lambda: packaged)
    user, repo = _paths(tmp_path)
    result = load_sources(Scope.REPO, user_overlay=user, repo_overlay=repo)
    assert result.config == packaged
    assert set(result.provenance.values()) == {"packaged"}


@pytest.mark.parametrize(
    ("text", "name"), [("[cluade]\nx = 1\n", "cluade"), ("foo = 1\n", "foo")]
)
def test_s1_1_1_unknown_top_level_table_fails_with_path_and_name(
    tmp_path, monkeypatch, text, name
):
    monkeypatch.setattr(sources, "load_packaged", dict)
    user, repo = _paths(tmp_path)
    user.write_text(text)
    with pytest.raises(SourceError) as excinfo:
        load_sources(Scope.REPO, user_overlay=user, repo_overlay=repo)
    assert str(user) in excinfo.value.message
    assert name in excinfo.value.message


def test_s1_1_1_machine_scope_ignores_repo_overlay(tmp_path, monkeypatch):
    monkeypatch.setattr(sources, "load_packaged", dict)
    user, repo = _paths(tmp_path)
    user.write_text('[claude]\neffortLevel = "medium"\n')
    repo.write_text('[claude]\neffortLevel = "high"\n')
    result = load_sources(Scope.MACHINE, user_overlay=user, repo_overlay=repo)
    assert result.config["claude"]["effortLevel"] == "medium"
    assert "repo" not in result.provenance.values()
    repo.write_text("[claude")
    load_sources(Scope.MACHINE, user_overlay=user, repo_overlay=repo)


def test_s1_1_1_packaged_defaults_ship_for_each_agent():
    packaged = load_packaged()
    assert set(packaged) == {"claude", "codex"}
    assert all(isinstance(value, dict) for value in packaged.values())


def test_s1_1_1_overlay_paths():
    assert user_overlay_path(Path("/h")) == Path("/h/share/agentkit/config.toml")
    assert repo_overlay_path(Path("/r")) == Path("/r/.rn-forge/agentkit/config.toml")
