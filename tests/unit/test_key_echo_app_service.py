from adapters.inputs.base import KeyEventDecision
from application.keyboard import KeyboardInputService
from application.output_capabilities import OutputCapabilities
from application.speech_service import SpeechService
from remote_core.models.keys import KeyEvent
from remote_core.models.speech_sequence import SpeechSequence

from apps.key_echo.service import KeyEchoAppService
from apps.key_echo import main as main_module


class FakeSpeechOutput:
    def __init__(self) -> None:
        self.spoken: list[SpeechSequence] = []

    def speak(self, sequence: SpeechSequence) -> None:
        self.spoken.append(sequence)

    def cancel(self) -> None:
        return None

    def pause(self, is_paused: bool) -> None:
        return None

    def list_voices(self) -> tuple[tuple[str, str], ...]:
        return ()

    def get_voice(self) -> str | None:
        return None

    def set_voice(self, voice_id: str) -> None:
        return None

    def get_rate(self) -> int | None:
        return None

    def set_rate(self, value: int) -> None:
        return None

    def get_pitch(self) -> int | None:
        return None

    def set_pitch(self, value: int) -> None:
        return None

    def get_volume(self) -> int | None:
        return None

    def set_volume(self, value: int) -> None:
        return None


class FakeCapture:
    def __init__(self) -> None:
        self.listener = None
        self.start_calls = 0
        self.stop_calls = 0

    def set_listener(self, listener) -> None:
        self.listener = listener

    def start(self) -> None:
        self.start_calls += 1

    def stop(self) -> None:
        self.stop_calls += 1


def test_key_echo_app_service_speaks_vk_on_keydown() -> None:
    speech_output = FakeSpeechOutput()
    service = KeyEchoAppService(
        outputs=OutputCapabilities(speech=SpeechService.single_backend(speech_output))
    )

    event = KeyEvent(vk=65, scan=30, extended=False, pressed=True)
    decision = service.handle_key_event(event)

    assert decision == KeyEventDecision.PASS_THROUGH
    assert speech_output.spoken == [SpeechSequence(items=("VK 65",))]


def test_key_echo_app_service_ignores_keyup_for_speech() -> None:
    speech_output = FakeSpeechOutput()
    service = KeyEchoAppService(
        outputs=OutputCapabilities(speech=SpeechService.single_backend(speech_output))
    )

    event = KeyEvent(vk=65, scan=30, extended=False, pressed=False)
    decision = service.handle_key_event(event)

    assert decision == KeyEventDecision.PASS_THROUGH
    assert speech_output.spoken == []


def test_build_runtime_composes_local_keyboard_and_speech(monkeypatch) -> None:
    capture = FakeCapture()
    speech_output = FakeSpeechOutput()

    monkeypatch.setattr(main_module, "WindowsKeyboardCapture", lambda: capture)
    monkeypatch.setattr(
        main_module.Pyttsx3SpeechOutput,
        "load_default",
        classmethod(lambda cls: speech_output),
    )

    runtime = main_module.build_runtime()
    runtime.input_service.bind()

    decision = capture.listener(KeyEvent(vk=66, scan=48, extended=False, pressed=True))

    assert isinstance(runtime.input_service, KeyboardInputService)
    assert isinstance(runtime.app_service, KeyEchoAppService)
    assert runtime.capture is capture
    assert runtime.speech_service.get_selected_backend() == "default"
    assert decision == KeyEventDecision.PASS_THROUGH
    assert speech_output.spoken == [SpeechSequence(items=("VK 66",))]


def test_main_pumps_windows_messages_and_stops_capture(monkeypatch) -> None:
    capture = FakeCapture()
    speech_output = FakeSpeechOutput()
    pumped: list[str] = []

    monkeypatch.setattr(main_module, "WindowsKeyboardCapture", lambda: capture)
    monkeypatch.setattr(
        main_module.Pyttsx3SpeechOutput,
        "load_default",
        classmethod(lambda cls: speech_output),
    )

    def pump_messages() -> None:
        pumped.append("called")
        raise KeyboardInterrupt

    monkeypatch.setattr(main_module, "_pump_windows_messages", pump_messages)

    result = main_module.main()

    assert result == 0
    assert pumped == ["called"]
    assert capture.start_calls == 1
    assert capture.stop_calls == 1
