from pathlib import Path

import pytest

from adapters.inputs.captured_event import CapturedKeyEvent
from application.events import ErrorRaised, SpeechEngineChanged
from application.input.results import AppKeyEventResult, KeyboardPipelineResult
from application.keyboard import KeyboardInputService
from application.output import Capabilities
from apps.access8graph.events import GraphNavigationChanged
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

    def get_engine_options(self):
        return (("default", "Default"),)

    def get_selected_engine(self):
        return self.backend_id

    def set_engine(self, engine_id):
        self.backend_id = engine_id

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
        capabilities=Capabilities(speech=speech),
    )
    input_service = KeyboardInputService(input_capture, service)
    service.attach_input_service(input_service)
    service.bind()
    return service, input_capture, hotkey_capture, speech


def test_service_dispatches_status_updates_through_main_thread_callback() -> None:
    pending = []
    delivered = []
    input_capture = FakeCapture()
    hotkey_capture = FakeHotkeyCapture()
    speech = FakeSpeech()
    service = Access8GraphAppService(
        hotkey_capture=hotkey_capture,
        input_capture=input_capture,
        capabilities=Capabilities(speech=speech),
        main_thread_dispatch=pending.append,
    )
    service.set_status_listener(delivered.append)

    service.set_speech_engine("default")

    assert delivered == []
    assert len(pending) == 1

    pending.pop()()

    assert delivered == [SpeechEngineChanged("default")]


def test_idle_hotkey_without_selected_graphml_reports_error_without_starting_capture() -> None:
    pending = []
    delivered = []
    input_capture = FakeCapture()
    hotkey_capture = FakeHotkeyCapture()
    speech = FakeSpeech()
    service = Access8GraphAppService(
        hotkey_capture=hotkey_capture,
        input_capture=input_capture,
        capabilities=Capabilities(speech=speech),
        main_thread_dispatch=pending.append,
    )
    input_service = KeyboardInputService(input_capture, service)
    service.attach_input_service(input_service)
    service.bind()
    service.set_status_listener(delivered.append)

    hotkey_capture.handler()

    assert service.is_navigation_running() is False
    assert input_capture.running is False
    assert len(pending) == 1

    pending.pop(0)()

    assert service.is_navigation_running() is False
    assert input_capture.running is False
    assert len(pending) == 1

    pending.pop(0)()

    assert delivered == [ErrorRaised("No GraphML file selected")]
    assert ("speak", SpeechSequence(items=("No GraphML file selected",))) in speech.calls


def test_idle_hotkey_with_malformed_graphml_keeps_specific_error_message(
    tmp_path: Path,
) -> None:
    pending = []
    delivered = []
    input_capture = FakeCapture()
    hotkey_capture = FakeHotkeyCapture()
    speech = FakeSpeech()
    service = Access8GraphAppService(
        hotkey_capture=hotkey_capture,
        input_capture=input_capture,
        capabilities=Capabilities(speech=speech),
        main_thread_dispatch=pending.append,
    )
    input_service = KeyboardInputService(input_capture, service)
    service.attach_input_service(input_service)
    service.bind()
    service.set_status_listener(delivered.append)

    path = tmp_path / "bad.graphml"
    path.write_text("not valid xml <<<", encoding="utf-8")
    service.choose_graphml(str(path))
    hotkey_capture.start()

    hotkey_capture.handler()

    while pending:
        pending.pop(0)()

    assert service.is_navigation_running() is False
    assert input_capture.running is False
    assert hotkey_capture.running is True
    assert delivered == [
        ErrorRaised(
            "Failed to parse GraphML file: syntax error: line 1, column 0"
        )
    ]


def test_idle_hotkey_reports_generic_start_failure_when_no_specific_error_preceded() -> None:
    pending = []
    delivered = []
    input_capture = FakeCapture()
    hotkey_capture = FakeHotkeyCapture()
    speech = FakeSpeech()
    service = Access8GraphAppService(
        hotkey_capture=hotkey_capture,
        input_capture=input_capture,
        capabilities=Capabilities(speech=speech),
        main_thread_dispatch=pending.append,
    )
    input_service = KeyboardInputService(input_capture, service)
    service.attach_input_service(input_service)
    service.bind()
    service.set_status_listener(delivered.append)

    def fail_start() -> None:
        raise RuntimeError("Failed to start navigation")

    service.start_navigation = fail_start
    hotkey_capture.handler()

    while pending:
        pending.pop(0)()

    assert delivered == [ErrorRaised("Failed to start navigation")]


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


def test_service_dispatches_graph_navigation_state_changes() -> None:
    statuses = []
    service, _input_capture, _hotkey_capture, _speech = build_service()
    service.set_status_listener(statuses.append)

    service.choose_graphml(str(FIXTURE))
    service.start_navigation()
    service.stop_navigation()

    assert GraphNavigationChanged(active=True) in statuses
    assert GraphNavigationChanged(active=False) in statuses


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


@pytest.mark.parametrize("pressed", [True, False])
def test_service_suppresses_unsupported_key_events_while_navigation_running(
    pressed: bool,
) -> None:
    service, _input_capture, _hotkey_capture, _speech = build_service()
    service.choose_graphml(str(FIXTURE))
    service.start_navigation()

    result = service.handle_key_event(
        CapturedKeyEvent(
            key_event=KeyEvent(
                usage_page=HID.KEYBOARD_PAGE,
                usage=HID.F1,
                pressed=pressed,
            )
        )
    )

    assert result == KeyboardPipelineResult(
        send_to_system=False,
        app_result=AppKeyEventResult.HANDLED_STOP,
    )
    assert service.is_navigation_running() is True


def test_service_stops_navigation_and_reports_flow_dispatch_exception() -> None:
    class FailingFlow:
        def enter(self, command):
            raise RuntimeError("flow dispatch failed")

    statuses = []
    service, input_capture, _hotkey_capture, _speech = build_service()
    service.set_status_listener(statuses.append)
    service.choose_graphml(str(FIXTURE))
    service.start_navigation()
    service._flow = FailingFlow()

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
    assert service.is_navigation_running() is False
    assert input_capture.running is False
    assert ErrorRaised("flow dispatch failed") in statuses


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
