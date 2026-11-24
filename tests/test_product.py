from rn_forge.commons.findings import Severity
from rn_forge.tooling.install import Link, ToolHome, doctor

from rn_forge.agentkit import findings as findings_module
from rn_forge.agentkit.findings import check_jq
from rn_forge.agentkit.product import PRODUCT, check_share_dir, share_dir


def test_the_one_artifact_is_the_command_on_path():
    assert PRODUCT.artifacts() == (
        Link(
            "bin/agentkit",
            "bin/agentkit",
        ),
        Link(
            "completions/_agentkit",
            "completions/_agentkit",
        ),
    )


def test_s4_1_1_missing_jq_is_an_error(tmp_path, monkeypatch):
    monkeypatch.setattr(findings_module.shutil, "which", lambda name: None)
    (finding,) = check_jq(ToolHome("agentkit", tmp_path / "home"))
    assert finding.code == "agentkit.jq-missing"
    assert finding.severity is Severity.ERROR
    assert "jq" in finding.message


def test_s4_1_1_jq_present_is_clean(tmp_path, monkeypatch):
    monkeypatch.setattr(findings_module.shutil, "which", lambda name: "/usr/bin/jq")
    assert check_jq(ToolHome("agentkit", tmp_path / "home")) == []


def test_s4_1_1_unwritable_share_dir_is_an_error(tmp_path):
    home = ToolHome("agentkit", tmp_path / "home")
    share = share_dir(home)
    share.mkdir(parents=True)
    share.chmod(0o500)
    try:
        (finding,) = check_share_dir(home)
    finally:
        share.chmod(0o700)
    assert finding.code == "agentkit.share-unwritable"
    assert finding.severity is Severity.ERROR
    assert str(share) in finding.message


def test_s4_1_1_absent_share_dir_under_a_writable_home_is_clean(tmp_path):
    home = ToolHome("agentkit", tmp_path / "home")
    home.root.mkdir()
    assert check_share_dir(home) == []


def test_s4_1_1_lifecycle_doctor_reports_both_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(findings_module.shutil, "which", lambda name: None)
    home = ToolHome("agentkit", tmp_path / "home")
    share = share_dir(home)
    share.mkdir(parents=True)
    share.chmod(0o500)
    try:
        findings = doctor(PRODUCT, home=home)
    finally:
        share.chmod(0o700)
    severities = {f.code: f.severity for f in findings}
    assert severities["agentkit.jq-missing"] is Severity.ERROR
    assert severities["agentkit.share-unwritable"] is Severity.ERROR
