import tarfile
from pathlib import Path

from rn_forge.commons.runtime.subprocess import Process
from rn_forge.tooling.install import LocalArchive, ToolHome, install, uninstall

from rn_forge.agentkit.product import PRODUCT, share_dir


def test_s4_1_1_installs_from_a_local_archive_and_uninstall_keeps_share(tmp_path):
    root = Path(__file__).parents[1]
    prefix = f"agentkit-{PRODUCT.version}"
    archive = tmp_path / f"{prefix}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(root / "pyproject.toml", f"{prefix}/pyproject.toml")
        tar.add(root / "README.md", f"{prefix}/README.md")
        for path in sorted((root / "src").rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                tar.add(path, f"{prefix}/{path.relative_to(root)}")
    home = ToolHome("agentkit", tmp_path / "home")

    install(PRODUCT, source=LocalArchive(archive, PRODUCT.version), home=home)

    assert home.version_dir(PRODUCT.version).is_dir()
    assert home.current.is_symlink()
    assert (home.root / "bin" / "agentkit").exists()
    result = Process.execute("run", str(home.root / "bin" / "agentkit"), "--version")
    assert result.stdout == f"{PRODUCT.version}\n"

    marker = share_dir(home) / "marker"
    marker.parent.mkdir(parents=True)
    marker.write_text("keep")
    uninstall(PRODUCT, home=home)
    assert marker.exists()
    assert not home.product_dir.exists()
