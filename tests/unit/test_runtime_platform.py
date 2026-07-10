import importlib
import logging
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import accessibility_toolkit.runtime.platform as _bp

from accessibility_toolkit.runtime.platform import (
    create_input_capture,
    create_hotkey_capture,
    create_clipboard_service,
    create_tone_output,
    default_speech_engine_id,
    default_speech_engine_options,
    PlatformProvider,
)
from accessibility_toolkit.input import HID


class TestDefaultSpeechEngineId:
    def test_windows_returns_nvda_controller(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "win32")
        assert default_speech_engine_id() == "NvdaController"

    def test_darwin_returns_pyttsx3(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "darwin")
        assert default_speech_engine_id() == "Pyttsx3"

    def test_other_platform_returns_pyttsx3(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        assert default_speech_engine_id() == "Pyttsx3"


def test_isolated_import_keeps_output_implementations_lazy():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "import accessibility_toolkit.runtime.platform; "
                "forbidden = {"
                "'accessibility_toolkit.output.tone', "
                "'accessibility_toolkit.output.speech.drivers.pyttsx3', "
                "'accessibility_toolkit.output.speech.windows.nvda_controller', "
                "'accessibility_toolkit.output.windows.clipboard'}; "
                "loaded = forbidden.intersection(sys.modules); "
                "assert not loaded, sorted(loaded)"
            ),
        ],
        check=False,
        capture_output=True,
        cwd=Path(__file__).resolve().parents[2] / "src",
        text=True,
    )

    assert result.returncode == 0, result.stderr

class TestDefaultSpeechEngineOptions:
    def test_windows_includes_nvda_controller_and_pyttsx3(self, monkeypatch):
        from accessibility_toolkit.scheduling import Scheduler

        monkeypatch.setattr(sys, "platform", "win32")
        scheduler = Scheduler()
        try:
            options = default_speech_engine_options(scheduler)
            ids = [(opt.engine_id, opt.label) for opt in options]
            assert ids == [
                ("NvdaController", "Nvda Controller"),
                ("Pyttsx3", "Pyttsx3"),
            ]
        finally:
            scheduler.shutdown()

    def test_non_windows_includes_only_pyttsx3(self, monkeypatch):
        from accessibility_toolkit.scheduling import Scheduler

        monkeypatch.setattr(sys, "platform", "darwin")
        scheduler = Scheduler()
        try:
            options = default_speech_engine_options(scheduler)
            ids = [(opt.engine_id, opt.label) for opt in options]
            assert ids == [("Pyttsx3", "Pyttsx3")]
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

    def test_windows_enter_vk_uses_enter_vk(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "win32")

        class FakeWindowsHotkeyCapture:
            def __init__(self, *, usage, label):
                self.usage = usage
                self.label = label

        monkeypatch.setattr(_bp, "_WindowsHotkeyCapture", FakeWindowsHotkeyCapture)

        capture = create_hotkey_capture(HID.ENTER)

        assert capture.usage == HID.ENTER
        assert capture.label == "HID_0x28"

    def test_macos_enter_vk_uses_return_key_code(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "darwin")

        class FakeMacHotkeyCapture:
            def __init__(self, *, manager, key_code):
                self.manager = manager
                self.key_code = key_code

        monkeypatch.setattr(_bp, "_MacOSHotkeyCapture", FakeMacHotkeyCapture)
        monkeypatch.setattr(_bp, "_macos_event_tap_manager_instance", object())

        capture = create_hotkey_capture(HID.ENTER)

        assert capture.key_code == 36

    def test_macos_f10_vk_uses_f10_key_code(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "darwin")

        class FakeMacHotkeyCapture:
            def __init__(self, *, manager, key_code):
                self.manager = manager
                self.key_code = key_code

        monkeypatch.setattr(_bp, "_MacOSHotkeyCapture", FakeMacHotkeyCapture)
        monkeypatch.setattr(_bp, "_macos_event_tap_manager_instance", object())

        capture = create_hotkey_capture(HID.F10)

        assert capture.key_code == 109


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
        fake_event_tap = ModuleType("accessibility_toolkit.input.macos.event_tap")
        fake_event_tap.MacOSEventTapManager = type(
            "FakeEventTapManager", (), {"__init__": lambda self, permissions, backend: None}
        )
        fake_event_tap.QuartzEventTapBackend = type(
            "FakeQuartzBackend", (), {}
        )
        monkeypatch.setitem(sys.modules, "accessibility_toolkit.input.macos.event_tap", fake_event_tap)
        importlib.invalidate_caches()

        fake_keyboard_hook = ModuleType("accessibility_toolkit.input.macos.keyboard_hook")
        fake_keyboard_hook.MacOSKeyboardCapture = type(
            "FakeMacKeyboardCapture", (), {"__init__": lambda self, manager: None}
        )
        monkeypatch.setitem(
            sys.modules, "accessibility_toolkit.input.macos.keyboard_hook", fake_keyboard_hook
        )

        fake_hotkey = ModuleType("accessibility_toolkit.input.macos.hotkey")
        fake_hotkey.MacOSHotkeyCapture = type(
            "FakeMacHotkeyCapture", (), {"__init__": lambda self, manager, key_code=103: None}
        )
        monkeypatch.setitem(sys.modules, "accessibility_toolkit.input.macos.hotkey", fake_hotkey)

        fake_permissions = ModuleType("accessibility_toolkit.input.macos.permissions")
        fake_permissions.AccessibilityPermissions = type(
            "FakePermissions",
            (),
            {"load_default": classmethod(lambda cls: type("FakePerm", (), {})())},
        )
        monkeypatch.setitem(
            sys.modules, "accessibility_toolkit.input.macos.permissions", fake_permissions
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


class TestCreateToneOutput:
    def test_returns_default_tone_output(self):
        from accessibility_toolkit.output.tone import DefaultToneOutput

        tone = create_tone_output()

        assert isinstance(tone, DefaultToneOutput)


class TestPlatformProvider:
    def test_build_services_on_linux_uses_fallback_platform_services(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")

        services = PlatformProvider().build_services(hotkey_usage=HID.ENTER)

        assert not services.input_capture.running
        assert not services.hotkey_capture.running
        assert services.clipboard.get_text() == ""
        assert services.tone_output is not None
        assert PlatformProvider().default_speech_engine_id() == "Pyttsx3"
