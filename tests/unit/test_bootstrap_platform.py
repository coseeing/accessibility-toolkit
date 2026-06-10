import logging
import sys

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
