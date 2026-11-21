import json
import subprocess

import pytest
from rn_forge.cli import ExitCode, run
from rn_forge.commons.fs.blocks import ManagedBlock

from rn_forge.agentkit.main import app

BLOCK = (
    "# BEGIN rn-forge agentkit\n"
    ".rn-forge/agentkit/backups/\n"
    ".rn-forge/agentkit/.staging/\n"
    ".rn-forge/agentkit/state.lock\n"
    "# END rn-forge agentkit\n"
)
KILN_GITIGNORE = (
    ".venv\n\n# BEGIN rn-forge kiln\n.rn-forge/kiln/backups/\n"
    ".rn-forge/kiln/state.lock\n# END rn-forge kiln\n"
)


@pytest.fixture
def home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("RNF_HOME", str(home / ".rn-forge"))
    return home


@pytest.fixture
def repo(tmp_path):
    repo = tmp_path / "myrepo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    return repo


def apply_args(repo):
    return ["apply", "--scope", "repo", "--repo", str(repo)]


def test_s2_2_3_absent_gitignore_is_created_with_the_block(home, repo):
    assert run(app, apply_args(repo)) == ExitCode.OK
    assert (repo / ".gitignore").read_text() == BLOCK


def test_s2_2_3_kiln_block_is_byte_identical(home, repo, capsys):
    kiln = ManagedBlock("rn-forge kiln")
    (repo / ".gitignore").write_text(KILN_GITIGNORE)
    before = kiln.extract(KILN_GITIGNORE)
    assert run(app, apply_args(repo)) == ExitCode.OK
    text = (repo / ".gitignore").read_text()
    assert text == KILN_GITIGNORE + "\n" + BLOCK
    assert kiln.extract(text) == before
    capsys.readouterr()
    args = apply_args(repo)
    assert run(app, ["--json", *args]) == ExitCode.OK
    actions = {c["path"]: c["action"] for c in json.loads(capsys.readouterr().out)}
    assert actions[".gitignore"] == "unchanged"


def test_s2_2_3_derived_files_ignored_state_tracked(home, repo):
    assert run(app, apply_args(repo)) == ExitCode.OK
    expected = {
        ".rn-forge/agentkit/backups/x": 0,
        ".rn-forge/agentkit/.staging/x": 0,
        ".rn-forge/agentkit/state.lock": 0,
        ".rn-forge/agentkit/state.json": 1,
        ".rn-forge/agentkit/config.toml": 1,
    }
    for path in expected:
        file = repo / path
        if not file.exists():
            file.parent.mkdir(parents=True, exist_ok=True)
            file.touch()
    for path, code in expected.items():
        result = subprocess.run(
            ["git", "check-ignore", "-q", path], check=False, cwd=repo
        )
        assert result.returncode == code, path
