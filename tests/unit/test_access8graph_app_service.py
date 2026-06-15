from pathlib import Path

import pytest

from adapters.inputs.captured_event import CapturedKeyEvent
from application.input.results import AppKeyEventResult, KeyboardPipelineResult
from application.keyboard import KeyboardInputService
from application.output_capabilities import OutputCapabilities
from apps.access8graph.service import Access8GraphAppService
from interop.key import HID, KeyEvent
from interop.speech.speech_sequence import SpeechSequence


FIXTURE = Path("Access8Graph/tests/test.graphml")


class FakeSpeech:
    def __init__(self) -> None:
        self.calls = []
        self.backend_id = "default"

    def speak(self, sequence: SpeechSequence) -> None:
        self.calls.append(("speak", sequence))

    def cancel(self) -> None:
        self.calls.append(("cancel", None))

    def pause(self, is_paused: bool) -> None:
        self.calls.append(("pause", is_paused))

    def get_backend_options(self):
        return (("default", "Default"),)

    def get_selected_backend(self):
        return self.backend_id

    def set_backend(self, backend_id):
        self.backend_id = backend_id

    def list_voices(self):
        return ()

    def get_voice(self):
        return None

    def set_voice(self, voice_id):
        self.calls.append(("set_voice", voice_id))

    def get_rate(self):
        return None

    def set_rate(self, value):
        self.calls.append(("set_rate", value))

    def get_pitch(self):
        return None

    def set_pitch(self, value):
        self.calls.append(("set_pitch", value))

    def get_volume(self):
        return None

    def set_volume(self, value):
        self.calls.append(("set_volume", value))

    def shutdown(self):
        self.calls.append(("shutdown", None))


class FakeCapture:
    def __init__(self) -> None:
        self.listener = None
        self.start_calls = 0
        self.stop_calls = 0

    @property
    def running(self) -> bool:
        return self.start_calls > self.stop_calls

    def set_listener(self, listener) -> None:
        self.listener = listener

    def start(self) -> None:
        self.start_calls += 1

    def stop(self) -> None:
        self.stop_calls += 1


class FakeHotkeyCapture(FakeCapture):
    def set_handler(self, handler) -> None:
        self.handler = handler


def build_service():
    input_capture = FakeCapture()
    hotkey_capture = FakeHotkeyCapture()
    speech = FakeSpeech()
    service = Access8GraphAppService(
        hotkey_capture=hotkey_capture,
        input_capture=input_capture,
        outputs=OutputCapabilities(speech=speech),
    )
    input_service = KeyboardInputService(input_capture, service)
    service.attach_input_service(input_service)
    service.bind()
    return service, input_capture, hotkey_capture, speech


def test_service_cannot_start_without_selected_graphml() -> None:
    service, input_capture, _hotkey_capture, _speech = build_service()

    with pytest.raises(RuntimeError, match="No GraphML file selected"):
        service.start_navigation()

    assert service.is_navigation_running() is False
    assert input_capture.running is False


def test_service_rejects_non_graphml_path(tmp_path: Path) -> None:
    service, _input_capture, _hotkey_capture, _speech = build_service()
    path = tmp_path / "graph.txt"
    path.write_text("<graphml />", encoding="utf-8")

    with pytest.raises(ValueError, match="\\.graphml"):
        service.choose_graphml(str(path))


def test_service_starts_and_stops_navigation() -> None:
    service, input_capture, _hotkey_capture, speech = build_service()

    service.choose_graphml(str(FIXTURE))
    service.start_navigation()

    assert service.is_navigation_running() is True
    assert input_capture.running is True
    assert any(call[0] == "speak" for call in speech.calls)

    service.stop_navigation()

    assert service.is_navigation_running() is False
    assert input_capture.running is False


def test_service_handles_key_event_while_navigation_running() -> None:
    service, _input_capture, _hotkey_capture, _speech = build_service()
    service.choose_graphml(str(FIXTURE))
    service.start_navigation()

    result = service.handle_key_event(
        CapturedKeyEvent(
            key_event=KeyEvent(
                usage_page=HID.KEYBOARD_PAGE,
                usage=HID.DOWN,
                pressed=True,
            )
        )
    )

    assert result == KeyboardPipelineResult(
        send_to_system=False,
        app_result=AppKeyEventResult.HANDLED_STOP,
    )


def test_service_escape_stops_navigation() -> None:
    service, _input_capture, _hotkey_capture, _speech = build_service()
    service.choose_graphml(str(FIXTURE))
    service.start_navigation()

    result = service.handle_key_event(
        CapturedKeyEvent(
            key_event=KeyEvent(
                usage_page=HID.KEYBOARD_PAGE,
                usage=HID.ESCAPE,
                pressed=True,
            )
        )
    )

    assert result == KeyboardPipelineResult(
        send_to_system=False,
        app_result=AppKeyEventResult.HANDLED_STOP,
    )
    assert service.is_navigation_running() is False


def test_service_rejects_non_existent_file_in_choose_graphml() -> None:
    service, _input_capture, _hotkey_capture, _speech = build_service()

    with pytest.raises(FileNotFoundError):
        service.choose_graphml("/nonexistent/path.graphml")


def test_service_accepts_uppercase_graphml_suffix(tmp_path: Path) -> None:
    service, _input_capture, _hotkey_capture, _speech = build_service()
    path = tmp_path / "map.GRAPHML"
    path.write_text("<graphml />", encoding="utf-8")

    service.choose_graphml(str(path))

    assert service.get_selected_graphml_path() == str(path)


def test_service_malformed_graphml_does_not_leave_input_capture_running(
    tmp_path: Path,
) -> None:
    service, input_capture, hotkey_capture, _speech = build_service()
    path = tmp_path / "bad.graphml"
    path.write_text("not valid xml <<<", encoding="utf-8")
    service.choose_graphml(str(path))
    hotkey_capture.start()

    with pytest.raises(RuntimeError, match="Failed to start"):
        service.start_navigation()

    assert service.is_navigation_running() is False
    assert input_capture.running is False
    assert hotkey_capture.running is True


def test_service_deleted_file_fails_before_activation(tmp_path: Path) -> None:
    service, input_capture, hotkey_capture, _speech = build_service()
    path = tmp_path / "will_be_deleted.graphml"
    path.write_text("<graphml />", encoding="utf-8")
    service.choose_graphml(str(path))
    path.unlink()
    hotkey_capture.start()

    with pytest.raises(FileNotFoundError):
        service.start_navigation()

    assert service.is_navigation_running() is False
    assert input_capture.running is False
    assert hotkey_capture.running is True
