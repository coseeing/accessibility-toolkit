import shutil
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path

import pytest


pytest.importorskip("setuptools", reason="distribution packaging checks require the optional build backend")


REPOSITORY_ROOT = Path(__file__).parents[2]


def _build_distribution(tmp_path: Path, project_name: str, source_package: str) -> tuple[Path, Path]:
    repository = tmp_path / "repository"
    project = repository / "packages" / project_name
    shutil.copytree(REPOSITORY_ROOT / "packages" / project_name, project)
    shutil.copytree(REPOSITORY_ROOT / "src" / source_package, repository / "src" / source_package)

    output = tmp_path / "dist"
    output.mkdir()
    pyproject = tomllib.loads((project / "pyproject.toml").read_text())
    backend_module = pyproject["build-system"]["build-backend"].partition(":")[0]
    sdist_result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import importlib, sys; importlib.import_module(sys.argv[1]).build_sdist(sys.argv[2])",
            backend_module,
            str(output),
        ],
        cwd=project,
        capture_output=True,
        text=True,
    )
    assert sdist_result.returncode == 0, sdist_result.stdout + sdist_result.stderr

    sdists = list(output.glob("*.tar.gz"))
    assert len(sdists) == 1
    wheel_result = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--no-deps", "--wheel-dir", str(output), str(sdists[0])],
        cwd=repository,
        capture_output=True,
        text=True,
    )
    assert wheel_result.returncode == 0, wheel_result.stdout + wheel_result.stderr

    wheels = list(output.glob("*.whl"))
    assert len(wheels) == 1
    return wheels[0], sdists[0]


def test_core_sdist_rebuilds_wheel_with_only_core_and_nvda_dll(tmp_path):
    wheel, sdist = _build_distribution(tmp_path, "accessibility-toolkit-core", "accessibility_toolkit")

    with zipfile.ZipFile(wheel) as archive:
        wheel_files = set(archive.namelist())
    assert "accessibility_toolkit/__init__.py" in wheel_files
    assert not any(name.startswith("accessibility_toolkit_wx/") for name in wheel_files)
    assert (
        "accessibility_toolkit/output/speech/windows/vendor/nvda/x64/nvdaControllerClient.dll"
        in wheel_files
    )

    with tarfile.open(sdist, "r:gz") as archive:
        sdist_files = set(archive.getnames())
    assert any(name.endswith("/src/accessibility_toolkit/__init__.py") for name in sdist_files)
    assert not any("/accessibility_toolkit_wx/" in name for name in sdist_files)
    assert any(name.endswith("/vendor/nvda/x64/nvdaControllerClient.dll") for name in sdist_files)


def test_wx_sdist_rebuilds_wheel_with_only_wx_package(tmp_path):
    wheel, sdist = _build_distribution(tmp_path, "accessibility-toolkit-wx", "accessibility_toolkit_wx")

    with zipfile.ZipFile(wheel) as archive:
        wheel_files = set(archive.namelist())
    assert "accessibility_toolkit_wx/__init__.py" in wheel_files
    assert not any(name.startswith("accessibility_toolkit/") for name in wheel_files)

    with tarfile.open(sdist, "r:gz") as archive:
        sdist_files = set(archive.getnames())
    assert any(name.endswith("/src/accessibility_toolkit_wx/__init__.py") for name in sdist_files)
    assert not any("/accessibility_toolkit/" in name for name in sdist_files)
