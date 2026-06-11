import importlib
import logging
import sys
from types import ModuleType

import bootstrap.platform as _bp

from bootstrap.platform import (
    create_input_capture,
    create_hotkey_capture,
    create_clipboard_service,
    default_speech_backend_id,
    default_speech_backend_options,
)


class TestDefaultSpeechBackendId:
    def test_windows_returns_nvda_controller(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "win32")
        assert default_speech_backend_id() == "nvda_controller"

    def test_darwin_returns_pyttsx3(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "darwin")
        assert default_speech_backend_id() == "pyttsx3"

    def test_other_platform_returns_pyttsx3(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        assert default_speech_backend_id() == "pyttsx3"


class TestDefaultSpeechBackendOptions:
    def test_windows_includes_nvda_controller_and_pyttsx3(self, monkeypatch):
        from application.output_scheduler import OutputScheduler

        monkeypatch.setattr(sys, "platform", "win32")
        scheduler = OutputScheduler()
        try:
            options = default_speech_backend_options(scheduler)
            ids = [opt.backend_id for opt in options]
            assert ids == ["nvda_controller", "pyttsx3"]
        finally:
            scheduler.shutdown()

    def test_non_windows_includes_only_pyttsx3(self, monkeypatch):
        from application.output_scheduler import OutputScheduler

        monkeypatch.setattr(sys, "platform", "darwin")
        scheduler = OutputScheduler()
        try:
            options = default_speech_backend_options(scheduler)
            ids = [opt.backend_id for opt in options]
            assert ids == ["pyttsx3"]
        finally:
            scheduler.shutdown()


class TestCreateInputCapture:
    def test_unsupported_platform_returns_null_capture(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        capture = create_input_capture()

        assert not capture.running
        capture.stop()


class TestCreateHotkeyCapture:
    def test_unsupported_platform_returns_null_capture(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        capture = create_hotkey_capture()

        assert not capture.running
        capture.stop()


class TestCreateClipboardService:
    def test_unsupported_platform_returns_fallback(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        clipboard = create_clipboard_service()

        assert clipboard.get_text() == ""
        clipboard.set_text("test")
        assert clipboard.get_text() == ""


class TestNullInputCapture:
    def test_start_logs_warning(self, monkeypatch, caplog):
        monkeypatch.setattr(sys, "platform", "linux")
        capture = create_input_capture()

        with caplog.at_level(logging.WARNING):
            capture.start()

        assert "InputCapture is not supported on this platform" in caplog.text

    def test_running_is_false(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        capture = create_input_capture()

        assert not capture.running

    def test_set_listener_does_not_crash(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        capture = create_input_capture()

        capture.set_listener(lambda e: "pass_through")


class TestNullHotkeyCapture:
    def test_start_logs_warning(self, monkeypatch, caplog):
        monkeypatch.setattr(sys, "platform", "linux")
        capture = create_hotkey_capture()

        with caplog.at_level(logging.WARNING):
            capture.start()

        assert "HotkeyCapture is not supported on this platform" in caplog.text

    def test_running_is_false(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        capture = create_hotkey_capture()

        assert not capture.running

    def test_set_handler_does_not_crash(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        capture = create_hotkey_capture()

        capture.set_handler(lambda: None)


class TestMacOSFactoriesWithColdGlobals:
    """Verify macOS factory functions work when all lazy-load globals are still None."""

    @staticmethod
    def _register_fake_macos_modules(monkeypatch):
        fake_event_tap = ModuleType("adapters.macos.event_tap")
        fake_event_tap.MacOSEventTapManager = type(
            "FakeEventTapManager", (), {"__init__": lambda self, permissions, backend: None}
        )
        fake_event_tap.QuartzEventTapBackend = type(
            "FakeQuartzBackend", (), {}
        )
        monkeypatch.setitem(sys.modules, "adapters.macos.event_tap", fake_event_tap)
        importlib.invalidate_caches()

        fake_keyboard_hook = ModuleType("adapters.macos.keyboard_hook")
        fake_keyboard_hook.MacOSKeyboardCapture = type(
            "FakeMacKeyboardCapture", (), {"__init__": lambda self, manager: None}
        )
        monkeypatch.setitem(
            sys.modules, "adapters.macos.keyboard_hook", fake_keyboard_hook
        )

        fake_hotkey = ModuleType("adapters.macos.hotkey")
        fake_hotkey.MacOSHotkeyCapture = type(
            "FakeMacHotkeyCapture", (), {"__init__": lambda self, manager: None}
        )
        monkeypatch.setitem(sys.modules, "adapters.macos.hotkey", fake_hotkey)

        fake_permissions = ModuleType("adapters.macos.permissions")
        fake_permissions.AccessibilityPermissions = type(
            "FakePermissions",
            (),
            {"load_default": classmethod(lambda cls: type("FakePerm", (), {})())},
        )
        monkeypatch.setitem(
            sys.modules, "adapters.macos.permissions", fake_permissions
        )
        importlib.invalidate_caches()

    @staticmethod
    def _reset_macos_lazy_globals():
        _bp._MacOSEventTapManager = None
        _bp._MacOSEventTapBackend = None
        _bp._MacOSKeyboardCapture = None
        _bp._MacOSHotkeyCapture = None
        _bp._AccessibilityPermissions = None
        _bp._macos_event_tap_manager_instance = None

    def test_create_input_capture_darwin_cold_globals(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "darwin")
        self._register_fake_macos_modules(monkeypatch)
        self._reset_macos_lazy_globals()

        capture = create_input_capture()

        assert capture is not None

    def test_create_hotkey_capture_darwin_cold_globals(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "darwin")
        self._register_fake_macos_modules(monkeypatch)
        self._reset_macos_lazy_globals()

        capture = create_hotkey_capture()

        assert capture is not None

    def test_event_tap_manager_is_shared_darwin(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "darwin")
        self._register_fake_macos_modules(monkeypatch)
        self._reset_macos_lazy_globals()

        capture_a = create_input_capture()
        capture_b = create_hotkey_capture()

        assert _bp._macos_event_tap_manager_instance is not None
        assert capture_a is not None
        assert capture_b is not None
