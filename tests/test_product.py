from rn_forge.commons.findings import Severity
from rn_forge.tooling.install import Link, ToolHome

from rn_forge.agentkit.product import PRODUCT


def test_the_one_artifact_is_the_command_on_path():
    assert PRODUCT.artifacts() == (
        Link(
            "bin/agentkit",
            "bin/agentkit",
        ),
    )


def test_the_one_check_reports_the_home(tmp_path):
    (check,) = PRODUCT.checks()
    (finding,) = check(ToolHome("agentkit", tmp_path))
    assert finding.code == "agentkit.home"
    assert finding.severity is Severity.INFO
