import logging
import sys
from pathlib import Path

import pytest

from bootstrap.runtime import (
    configure_logging,
    default_config_path,
    default_log_path,
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

        assert result == cwd / "nvda-remote-client.log"

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
    def test_returns_log_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sys, "frozen", False, raising=False)
        log_path = tmp_path / "test.log"

        result = configure_logging(log_path=log_path)

        assert result == log_path
        assert log_path.exists()

    def test_uses_warning_level(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr(sys, "frozen", False, raising=False)
        log_path = tmp_path / "test.log"

        configure_logging(log_path=log_path)

        test_logger = logging.getLogger("test_configure")
        test_logger.warning("hello bootstrap")

        content = log_path.read_text(encoding="utf-8")
        assert "hello bootstrap" in content
