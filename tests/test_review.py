import json
import subprocess

import pytest
from rn_forge.cli import ExitCode, run
from rn_forge.commons.fs.blocks import ManagedBlock

from rn_forge.agentkit.adapters.instructions import BLOCK
from rn_forge.agentkit.main import app
from rn_forge.agentkit.review import Suggestion, review
from rn_forge.agentkit.sources import Scope
from rn_forge.agentkit.targets import resolve_target

_MISSING_IMPORT = "# Claude\n\nNotes.\n"
_MALFORMED = "<!-- BEGIN rn-forge agentkit -->\n## A\n"
_KILN = ManagedBlock("rn-forge kiln", comment="<!--")


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


def _suggestions(home, repo=None):
    return review(
        resolve_target(
            Scope.MACHINE if repo is None else Scope.REPO,
            repo=repo,
            cwd=home.parent,
            home=home,
            rnf_home=home / ".rn-forge",
        )
    )


def test_s5_2_1_claude_md_without_import(home, repo):
    _write(repo, "CLAUDE.md", _MISSING_IMPORT)
    assert _suggestions(home, repo) == [
        Suggestion(
            "CLAUDE.md",
            _MISSING_IMPORT.splitlines().index("# Claude") + 1,
            "review.claude-import-missing",
            "CLAUDE.md does not import @AGENTS.md",
        )
    ]


def test_s5_2_1_claude_md_with_import_is_clean(home, repo):
    _write(repo, "CLAUDE.md", "@AGENTS.md\n\n## Claude-only\n")
    assert _suggestions(home, repo) == []


def test_s5_2_1_no_import_check_at_machine_scope(home):
    _write(home, ".claude/CLAUDE.md", _MISSING_IMPORT)
    assert _suggestions(home) == []


@pytest.mark.parametrize(
    ("scope", "path"),
    [
        ("machine", ".claude/CLAUDE.md"),
        ("machine", ".codex/AGENTS.md"),
        ("repo", "AGENTS.md"),
    ],
)
def test_s5_2_1_duplicate_heading_in_both_scopes(home, repo, scope, path):
    root = home if scope == "machine" else repo
    text = BLOCK.render("## Safety\n\n## Mine\n", "## Safety\n\n- x\n")
    _write(root, path, text)
    assert _suggestions(home, repo if scope == "repo" else None) == [
        Suggestion(
            path,
            text.splitlines().index("## Safety") + 1,
            "review.heading-duplicated",
            "heading 'Safety' repeats one in agentkit's block",
        )
    ]


def test_s5_2_1_heading_in_code_fence_is_ignored(home):
    _write(
        home,
        ".claude/CLAUDE.md",
        BLOCK.render("```markdown\n## Safety\n```\n", "## Safety\n\n- x\n"),
    )
    assert _suggestions(home) == []


def test_s5_2_1_agentkit_heading_duplicates_kiln_heading(home, repo):
    text = BLOCK.render(_KILN.render("", "## Agent workflow\n"), "## Agent workflow\n")
    _write(repo, "AGENTS.md", text)
    lines = text.splitlines()
    agentkit_start = lines.index("<!-- BEGIN rn-forge agentkit -->")
    assert _suggestions(home, repo) == [
        Suggestion(
            "AGENTS.md",
            lines.index("## Agent workflow", agentkit_start) + 1,
            "review.heading-duplicated",
            "heading 'Agent workflow' in agentkit's block repeats one in kiln's block",
        )
    ]


@pytest.mark.parametrize(
    ("scope", "path"), [("repo", "AGENTS.md"), ("machine", ".codex/AGENTS.md")]
)
def test_s5_2_1_agents_pointer(home, repo, scope, path):
    root = home if scope == "machine" else repo
    pointer = "**Read `CLAUDE.md` now and follow it.**"
    text = f"{pointer}\n"
    _write(root, path, text)
    assert _suggestions(home, repo if scope == "repo" else None) == [
        Suggestion(
            path,
            text.splitlines().index(pointer) + 1,
            "review.agents-points-at-claude",
            "AGENTS.md points at CLAUDE.md, which Codex cannot follow",
        )
    ]


def test_s5_2_1_agents_link_to_claude(home, repo):
    text = "# Agents\n\n[Claude](CLAUDE.md)\n"
    _write(repo, "AGENTS.md", text)
    assert _suggestions(home, repo) == [
        Suggestion(
            "AGENTS.md",
            text.splitlines().index("[Claude](CLAUDE.md)") + 1,
            "review.agents-points-at-claude",
            "AGENTS.md points at CLAUDE.md, which Codex cannot follow",
        )
    ]


def test_s5_2_1_body_heading_duplicates_kiln_heading(home, repo):
    text = _KILN.render("## Safety\n", "## Safety\n")
    _write(repo, "AGENTS.md", text)
    assert _suggestions(home, repo) == [
        Suggestion(
            "AGENTS.md",
            text.splitlines().index("## Safety") + 1,
            "review.heading-duplicated",
            "heading 'Safety' repeats one in kiln's block",
        )
    ]


def test_s5_2_1_repeated_claude_import(home, repo):
    text = "@AGENTS.md\n\n" + BLOCK.render("", "@AGENTS.md\n")
    _write(repo, "CLAUDE.md", text)
    assert _suggestions(home, repo) == [
        Suggestion(
            "CLAUDE.md",
            text.splitlines().index("@AGENTS.md") + 1,
            "review.import-repeated",
            "@AGENTS.md is in both the body and agentkit's block; delete it from the body",
        )
    ]


@pytest.mark.parametrize(
    "pattern",
    [
        "Replace this line",
        "Replace this section",
        "Instructions that only Claude Code should follow go here",
    ],
)
def test_s5_2_1_placeholder_only_in_body(home, repo, pattern):
    text = f"# Agents\n\n{pattern}.\n"
    _write(repo, "AGENTS.md", text)
    assert _suggestions(home, repo) == [
        Suggestion(
            "AGENTS.md",
            text.splitlines().index(f"{pattern}.") + 1,
            "review.placeholder",
            f"line still reads as template text: {pattern!r}",
        )
    ]

    _write(repo, "AGENTS.md", BLOCK.render("", text))
    assert _suggestions(home, repo) == []


def test_s5_2_1_malformed_block_suppresses_other_suggestions(home, repo):
    _write(repo, "CLAUDE.md", _MALFORMED)
    assert _suggestions(home, repo) == [
        Suggestion(
            "CLAUDE.md",
            _MALFORMED.splitlines().index("<!-- BEGIN rn-forge agentkit -->") + 1,
            "review.block-malformed",
            "agentkit's block markers are malformed; run agentkit doctor",
        )
    ]


def test_s5_2_1_review_command_clean_repo(home, repo, capsys):
    _write(repo, "AGENTS.md", "# A\n")
    _write(repo, "CLAUDE.md", "@AGENTS.md\n")

    assert run(app, ["review", "--scope", "repo", "--repo", str(repo)]) == ExitCode.OK
    assert capsys.readouterr().out == "no suggestions\n"


def test_s5_2_1_review_command_prints_suggestion(home, repo, capsys):
    _write(repo, "CLAUDE.md", _MISSING_IMPORT)

    assert run(app, ["review", "--scope", "repo", "--repo", str(repo)]) == ExitCode.OK
    assert capsys.readouterr().out == (
        "CLAUDE.md:1: review.claude-import-missing CLAUDE.md does not import @AGENTS.md\n"
    )


def test_s5_2_1_review_command_malformed_block_exits_ok(home, repo):
    _write(repo, "AGENTS.md", _MALFORMED)
    assert run(app, ["review", "--scope", "repo", "--repo", str(repo)]) == ExitCode.OK


def test_s5_2_1_review_command_json(home, repo, capsys):
    _write(repo, "CLAUDE.md", _MISSING_IMPORT)

    assert (
        run(app, ["--json", "review", "--scope", "repo", "--repo", str(repo)])
        == ExitCode.OK
    )
    assert json.loads(capsys.readouterr().out) == [
        {
            "path": "CLAUDE.md",
            "line": _MISSING_IMPORT.splitlines().index("# Claude") + 1,
            "code": "review.claude-import-missing",
            "message": "CLAUDE.md does not import @AGENTS.md",
        }
    ]


def test_s5_2_1_review_command_defaults_to_machine_scope(home, capsys):
    assert run(app, ["review"]) == ExitCode.OK
    assert capsys.readouterr().out == "no suggestions\n"
