from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import tempfile

from setuptools import build_meta as _setuptools_backend


_PROJECT_ROOT = Path(__file__).resolve().parent
_SOURCE_PACKAGE = "accessibility_toolkit"


@contextmanager
def _staged_project():
    local_source = _PROJECT_ROOT / "src" / _SOURCE_PACKAGE
    if local_source.is_dir():
        yield
        return

    repository_source = _PROJECT_ROOT.parents[1] / "src" / _SOURCE_PACKAGE
    if not repository_source.is_dir():
        raise RuntimeError(f"source package does not exist: {repository_source}")

    with tempfile.TemporaryDirectory(prefix="accessibility-toolkit-build-") as temporary_directory:
        staged_project = Path(temporary_directory) / "project"
        shutil.copytree(
            _PROJECT_ROOT,
            staged_project,
            ignore=shutil.ignore_patterns("build", "dist", "src", "*.egg-info", "__pycache__"),
        )
        shutil.copytree(repository_source, staged_project / "src" / _SOURCE_PACKAGE)

        original_directory = Path.cwd()
        os.chdir(staged_project)
        try:
            yield
        finally:
            os.chdir(original_directory)


def _run_hook(name, *args, **kwargs):
    with _staged_project():
        return getattr(_setuptools_backend, name)(*args, **kwargs)


def get_requires_for_build_sdist(config_settings=None):
    return _run_hook("get_requires_for_build_sdist", config_settings)


def build_sdist(sdist_directory, config_settings=None):
    return _run_hook("build_sdist", str(Path(sdist_directory).resolve()), config_settings)


def get_requires_for_build_wheel(config_settings=None):
    return _run_hook("get_requires_for_build_wheel", config_settings)


def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    return _run_hook(
        "prepare_metadata_for_build_wheel",
        str(Path(metadata_directory).resolve()),
        config_settings,
    )


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    if metadata_directory is not None:
        metadata_directory = str(Path(metadata_directory).resolve())
    return _run_hook(
        "build_wheel",
        str(Path(wheel_directory).resolve()),
        config_settings,
        metadata_directory,
    )
