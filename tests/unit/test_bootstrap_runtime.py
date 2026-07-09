import logging
import sys
from pathlib import Path

import pytest

from accessibility_toolkit.runtime.environment import (
    configure_logging,
    default_config_path,
    default_log_path,
    is_frozen,
    resource_path,
)


class TestDefaultLogPath:
    def test_dev_uses_cwd(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", False, raising=False)
        cwd = Path.cwd().resolve()

        result = default_log_path(app_name="test-app")

        assert result == cwd / "test-app.log"

    def test_dev_uses_default_app_name(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", False, raising=False)
        cwd = Path.cwd().resolve()

        result = default_log_path()

        assert result == cwd / "accessibility-toolkit.log"

    def test_frozen_darwin_logs_dir(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "platform", "darwin")

        result = default_log_path(app_name="my-app")

        assert result == Path.home() / "Library" / "Logs" / "my-app" / "my-app.log"

    def test_frozen_non_darwin_uses_executable_parent(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(sys, "executable", "/opt/my-app/app.exe")

        result = default_log_path(app_name="my-app")

        assert result == Path("/opt/my-app") / "my-app.log"


class TestDefaultConfigPath:
    def test_dev_uses_cwd(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", False, raising=False)
        cwd = Path.cwd().resolve()

        result = default_config_path(app_name="test-app")

        assert result == cwd / "test-app.json"

    def test_frozen_darwin_app_support_dir(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "platform", "darwin")

        result = default_config_path(app_name="my-app")

        assert result == Path.home() / "Library" / "Application Support" / "my-app" / "my-app.json"

    def test_frozen_non_darwin_uses_executable_parent(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(sys, "executable", "/opt/my-app/app.exe")

        result = default_config_path(app_name="my-app")

        assert result == Path("/opt/my-app") / "my-app.json"


class TestConfigureLogging:
    def test_defaults_to_disabled_without_env_var(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sys, "frozen", False, raising=False)
        log_path = tmp_path / "test.log"
        monkeypatch.delenv("ACCESSIBILITY_TOOLKIT_LOGGING", raising=False)

        result = configure_logging(log_path=log_path)

        assert result == log_path
        assert log_path.exists() is False

    def test_enables_file_logging_when_env_var_is_set(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sys, "frozen", False, raising=False)
        log_path = tmp_path / "test.log"
        monkeypatch.setenv("ACCESSIBILITY_TOOLKIT_LOGGING", "1")

        result = configure_logging(log_path=log_path)

        assert result == log_path
        assert log_path.exists()

    def test_uses_warning_level_when_enabled(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr(sys, "frozen", False, raising=False)
        log_path = tmp_path / "test.log"
        monkeypatch.setenv("ACCESSIBILITY_TOOLKIT_LOGGING", "true")

        configure_logging(log_path=log_path)

        test_logger = logging.getLogger("test_configure")
        test_logger.warning("hello bootstrap")

        content = log_path.read_text(encoding="utf-8")
        assert "hello bootstrap" in content


class TestRuntimeEnvironment:
    def test_is_frozen_uses_sys_frozen(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", True, raising=False)

        assert is_frozen() is True

    def test_resource_path_uses_repo_src_root_when_not_frozen(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", False, raising=False)

        result = resource_path("accessibility_toolkit")

        assert result.name == "accessibility_toolkit"
        assert result.parent.name == "src"

    def test_resource_path_uses_meipass_when_available(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", "/tmp/bundle", raising=False)

        result = resource_path("vendor/file.txt")

        assert result == Path("/tmp/bundle/vendor/file.txt")
