from pathlib import Path

import pytest


@pytest.fixture
def isolated_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, Path]:
    """Isolate HOME and RNF_HOME (under HOME) beneath pytest's temp directory."""
    home = tmp_path / "home"
    rnf = home / ".rn-forge"
    repo = tmp_path / "repo"
    home.mkdir()
    repo.mkdir()
    (repo / ".git").mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("RNF_HOME", str(rnf))
    return home, rnf, repo
