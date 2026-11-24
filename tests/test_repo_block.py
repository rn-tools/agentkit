import json
import subprocess

import pytest
from rn_forge.cli import ExitCode, run
from rn_forge.commons.fs.blocks import ManagedBlock

from rn_forge.agentkit import repository
from rn_forge.agentkit.main import app
from rn_forge.agentkit.repository import agents_block
from rn_forge.agentkit.sources import Scope, load_sources
from rn_forge.agentkit.targets import resolve_target

KILN_AGENTS = (
    "# AGENTS.md\n\nBody text.\n\n"
    "<!-- BEGIN rn-forge kiln -->\n## Repository standard (kiln)\n\n"
    "kiln text.\n<!-- END rn-forge kiln -->\n"
)

ALL_KEYS = (
    "[repo]\n"
    'worktree_root = "../{repo}-wt/"\n'
    "shared_checkout = true\n"
    'story_workflow = """Pick a story;\n  build it."""\n'
)

BLOCK = (
    "<!-- BEGIN rn-forge agentkit -->\n"
    "\n## Agent workflow\n\n"
    "- Worktrees: create each one under `../myrepo-wt/`.\n"
    "- Shared checkout: commit by explicit path, never `git add -A`, "
    "and re-check\n  HEAD before committing.\n"
    "- Story workflow: Pick a story; build it.\n\n"
    "<!-- END rn-forge agentkit -->\n"
)

KILN = ManagedBlock("rn-forge kiln", comment="<!--")


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
    (repo / "AGENTS.md").write_text(KILN_AGENTS)
    return repo


def overlay(repo, text):
    path = repo / ".rn-forge" / "agentkit" / "config.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def apply_repo(repo):
    return run(app, ["apply", "--scope", "repo", "--repo", str(repo)])


def test_s2_2_1_no_keys_no_block(home, repo, capsys):
    capsys.readouterr()
    code = run(app, ["--json", "plan", "--scope", "repo", "--repo", str(repo)])
    assert code == ExitCode.OK
    changes = json.loads(capsys.readouterr().out)["changes"]
    assert all(c["path"] != "AGENTS.md" for c in changes)
    assert apply_repo(repo) == ExitCode.OK
    assert (repo / "AGENTS.md").read_text() == KILN_AGENTS


def test_s2_2_1_block_lands_after_kiln_block(home, repo):
    before = KILN.extract(KILN_AGENTS)
    overlay(repo, ALL_KEYS)
    assert apply_repo(repo) == ExitCode.OK
    text = (repo / "AGENTS.md").read_text()
    assert text == KILN_AGENTS + "\n" + BLOCK
    assert KILN.extract(text) == before


def test_s2_2_1_unsetting_keys_removes_block(home, repo):
    overlay(repo, ALL_KEYS)
    assert apply_repo(repo) == ExitCode.OK
    overlay(repo, "")
    assert apply_repo(repo) == ExitCode.OK
    assert (repo / "AGENTS.md").read_text() == KILN_AGENTS


def test_s2_2_1_repo_placeholder_is_the_directory_name():
    assert agents_block({"worktree_root": "../{repo}-wt/"}, "myrepo") == (
        "\n## Agent workflow\n\n- Worktrees: create each one under `../myrepo-wt/`.\n\n"
    )


def test_s2_2_1_only_set_keys_render():
    assert agents_block({"shared_checkout": False, "story_workflow": ""}, "r") == ""
    body = agents_block({"shared_checkout": True}, "r")
    assert "Shared checkout" in body
    assert "Worktrees" not in body
    assert "Story workflow" not in body


def test_s2_2_1_bad_repo_key_fails(home, repo, capsys):
    overlay(repo, '[repo]\nworktree-root = "x"\n')
    capsys.readouterr()
    assert apply_repo(repo) == 1
    captured = capsys.readouterr()
    assert "'worktree-root'" in captured.out + captured.err
    overlay(repo, '[repo]\nshared_checkout = "yes"\n')
    capsys.readouterr()
    assert apply_repo(repo) == 1
    captured = capsys.readouterr()
    assert "'shared_checkout'" in captured.out + captured.err


def test_s2_2_1_machine_scope_renders_nothing(home, tmp_path):
    user = home / ".rn-forge" / "share" / "agentkit" / "config.toml"
    user.parent.mkdir(parents=True)
    user.write_text("[repo]\nshared_checkout = true\n")
    target = resolve_target(
        Scope.MACHINE,
        repo=None,
        cwd=tmp_path,
        home=home,
        rnf_home=home / ".rn-forge",
    )
    sources = load_sources(
        Scope.MACHINE,
        user_overlay=target.user_overlay,
        repo_overlay=target.repo_overlay,
    )
    assert repository.render(target, sources) == []


def test_s2_2_4_body_has_blank_lines_and_wraps():
    body = agents_block(
        {
            "worktree_root": "../{repo}-wt/",
            "shared_checkout": True,
            "story_workflow": "Pick a story;\n  build it.",
        },
        "myrepo",
    )
    assert body.startswith("\n## Agent workflow\n\n")
    assert body.endswith("\n\n")
    lines = body.splitlines()
    assert all(len(line) <= 80 for line in lines)
    shared = next(
        i for i, line in enumerate(lines) if line.startswith("- Shared checkout:")
    )
    assert lines[shared + 1].startswith("  ")
    assert lines[shared + 2].startswith("- Story workflow:")


@pytest.mark.parametrize(
    "config",
    [
        ALL_KEYS,
        '[repo]\nstory_workflow = "'
        + "Plan the work carefully and check the context before running "
        + "`a command with spaces` "
        + "then review the results and update the story with the outcome. " * 4
        + '"\n',
    ],
)
def test_s2_2_4_block_is_mdformat_stable(home, repo, config):
    mdformat = pytest.importorskip("mdformat")
    path = repo / "AGENTS.md"
    path.write_text(mdformat.text(KILN_AGENTS, options={"wrap": 80}))
    overlay(repo, config)
    assert apply_repo(repo) == ExitCode.OK
    text = path.read_text()
    assert mdformat.text(text, options={"wrap": 80}) == text


def test_s2_2_4_formatted_file_plans_unchanged(home, repo, capsys):
    mdformat = pytest.importorskip("mdformat")
    path = repo / "AGENTS.md"
    path.write_text(mdformat.text(KILN_AGENTS, options={"wrap": 80}))
    overlay(repo, ALL_KEYS)
    assert apply_repo(repo) == ExitCode.OK
    path.write_text(mdformat.text(path.read_text(), options={"wrap": 80}))
    capsys.readouterr()
    assert (
        run(app, ["--json", "plan", "--scope", "repo", "--repo", str(repo)])
        == ExitCode.OK
    )
    changes = json.loads(capsys.readouterr().out)["changes"]
    assert (
        next(change for change in changes if change["path"] == "AGENTS.md")["action"]
        == "unchanged"
    )


def test_s2_2_4_code_span_is_not_split():
    from rn_forge.agentkit.repository import _wrap

    span = "`a command with spaces`"
    wrapped = _wrap("- Story workflow: " + "word " * 10 + span + " afterward")
    assert span in wrapped.splitlines()[1]
