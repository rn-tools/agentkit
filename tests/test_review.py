import subprocess

import pytest
from rn_forge.commons.fs.blocks import ManagedBlock

from rn_forge.agentkit.adapters.instructions import BLOCK
from rn_forge.agentkit.review import review_findings
from rn_forge.agentkit.sources import Scope
from rn_forge.agentkit.targets import resolve_target


@pytest.fixture
def home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("RNF_HOME", str(home / ".rn-forge"))
    return home


@pytest.fixture
def repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    return repo


def _write(root, path, text):
    file = root / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text)


def _findings(home, repo=None):
    return review_findings(
        resolve_target(
            Scope.MACHINE if repo is None else Scope.REPO,
            repo=repo,
            cwd=home.parent,
            home=home,
            rnf_home=home / ".rn-forge",
        )
    )


def _warning(found, code, message):
    assert [f.code for f in found] == [code]
    assert found[0].severity == "warning"
    assert found[0].message == message


def test_s2_3_1_claude_md_without_import_warns(home, repo):
    _write(repo, "CLAUDE.md", "# Claude\n\nNotes.\n")
    _warning(
        _findings(home, repo),
        "agentkit.claude-import-missing",
        "CLAUDE.md does not import @AGENTS.md",
    )


def test_s2_3_1_claude_md_with_import_is_clean(home, repo):
    _write(repo, "CLAUDE.md", "@AGENTS.md\n\n## Claude-only\n")
    assert _findings(home, repo) == []


def test_s2_3_1_no_import_check_at_machine_scope(home):
    _write(home, ".claude/CLAUDE.md", "# Claude\n\nNotes.\n")
    assert _findings(home) == []


@pytest.mark.parametrize(
    ("scope", "path"),
    [
        ("machine", ".claude/CLAUDE.md"),
        ("machine", ".codex/AGENTS.md"),
        ("repo", "AGENTS.md"),
    ],
)
def test_s2_3_1_duplicate_heading_warns_both_scopes(home, repo, scope, path):
    root = home if scope == "machine" else repo
    _write(root, path, BLOCK.render("## Safety\n\n## Mine\n", "## Safety\n\n- x\n"))
    _warning(
        _findings(home, repo if scope == "repo" else None),
        "agentkit.heading-duplicated",
        f"{path}: heading 'Safety' is in both the body and agentkit's block",
    )


def test_s2_3_1_heading_in_code_fence_is_ignored(home):
    _write(
        home,
        ".claude/CLAUDE.md",
        BLOCK.render("```markdown\n## Safety\n```\n", "## Safety\n\n- x\n"),
    )
    assert _findings(home) == []


def test_s2_3_1_kiln_block_heading_counts_as_body(home, repo):
    kiln = ManagedBlock("rn-forge kiln", comment="<!--")
    text = kiln.render("", "## Agent workflow\n")
    _write(repo, "AGENTS.md", BLOCK.render(text, "## Agent workflow\n"))
    found = _findings(home, repo)
    assert all(f.code == "agentkit.heading-duplicated" for f in found)
    _warning(
        found,
        "agentkit.heading-duplicated",
        "AGENTS.md: heading 'Agent workflow' is in both the body and agentkit's block",
    )


@pytest.mark.parametrize(
    ("scope", "path"), [("repo", "AGENTS.md"), ("machine", ".codex/AGENTS.md")]
)
def test_s2_3_1_agents_pointer_warns(home, repo, scope, path):
    root = home if scope == "machine" else repo
    _write(root, path, "**Read `CLAUDE.md` now and follow it.**\n")
    _warning(
        _findings(home, repo if scope == "repo" else None),
        "agentkit.agents-points-at-claude",
        f"{path} points at CLAUDE.md as canonical; AGENTS.md is canonical",
    )


def test_s2_3_1_review_reports_machine_findings(home):
    _write(
        home,
        ".claude/CLAUDE.md",
        BLOCK.render("## Safety\n\n## Mine\n", "## Safety\n\n- x\n"),
    )
    found = _findings(home)
    matches = [f for f in found if f.code == "agentkit.heading-duplicated"]
    assert len(matches) == 1
    assert matches[0].message == (
        ".claude/CLAUDE.md: heading 'Safety' is in both the body and agentkit's block"
    )
