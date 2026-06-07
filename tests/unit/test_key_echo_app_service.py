import pytest

from adapters.inputs.base import KeyEventDecision
from application.keyboard import KeyboardInputService
from application.output_capabilities import OutputCapabilities
from application.speech_service import SpeechService
from interop.key.key_event import KeyEvent
from interop.speech.speech_sequence import SpeechSequence

from apps.key_echo.service import KeyEchoAppService
from apps.key_echo import main as main_module


class FakeSpeechOutput:
    def __init__(self) -> None:
        self.spoken: list[SpeechSequence] = []
        self.calls: list[tuple[str, SpeechSequence | None]] = []
        self.cancel_calls = 0
        self.voice_id: str | None = None
        self.rate: int | None = None
        self.pitch: int | None = None
        self.volume: int | None = None

    def speak(self, sequence: SpeechSequence) -> None:
        self.calls.append(("speak", sequence))
        self.spoken.append(sequence)

    def cancel(self) -> None:
        self.calls.append(("cancel", None))
        self.cancel_calls += 1
        return None

    def pause(self, is_paused: bool) -> None:
        return None

    def list_voices(self) -> tuple[tuple[str, str], ...]:
        return ()

    def get_voice(self) -> str | None:
        return self.voice_id

    def set_voice(self, voice_id: str) -> None:
        self.voice_id = voice_id

    def get_rate(self) -> int | None:
        return self.rate

    def set_rate(self, value: int) -> None:
        self.rate = value

    def get_pitch(self) -> int | None:
        return self.pitch

    def set_pitch(self, value: int) -> None:
        self.pitch = value

    def get_volume(self) -> int | None:
        return self.volume

    def set_volume(self, value: int) -> None:
        self.volume = value


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

    @property
    def running(self) -> bool:
        return self.start_calls > self.stop_calls


def test_key_echo_app_service_speaks_vk_on_keydown() -> None:
    speech_output = FakeSpeechOutput()
    service = KeyEchoAppService(
        outputs=OutputCapabilities(speech=SpeechService.single_backend(speech_output))
    )

    event = KeyEvent(vk=65, scan=30, extended=False, pressed=True)
    decision = service.handle_key_event(event)

    assert decision == KeyEventDecision.SUPPRESS
    assert speech_output.cancel_calls == 1
    assert speech_output.calls == [
        ("cancel", None),
        ("speak", SpeechSequence(items=("VK 65",))),
    ]
    assert speech_output.spoken == [SpeechSequence(items=("VK 65",))]


def test_key_echo_app_service_ignores_keyup_for_speech() -> None:
    speech_output = FakeSpeechOutput()
    service = KeyEchoAppService(
        outputs=OutputCapabilities(speech=SpeechService.single_backend(speech_output))
    )

    event = KeyEvent(vk=65, scan=30, extended=False, pressed=False)
    decision = service.handle_key_event(event)

    assert decision == KeyEventDecision.SUPPRESS
    assert speech_output.cancel_calls == 0
    assert speech_output.spoken == []


def test_key_echo_app_service_stops_echo_on_escape_keydown() -> None:
    capture = FakeCapture()
    speech_output = FakeSpeechOutput()
    service = KeyEchoAppService(
        outputs=OutputCapabilities(speech=SpeechService.single_backend(speech_output))
    )
    input_service = KeyboardInputService(capture, service)
    service.attach_input_service(input_service)
    service.start_echo()

    decision = service.handle_key_event(
        KeyEvent(vk=0x1B, scan=1, extended=False, pressed=True)
    )

    assert decision == KeyEventDecision.SUPPRESS
    assert capture.stop_calls == 1
    assert service.is_echo_running() is False
    assert speech_output.cancel_calls == 0
    assert speech_output.spoken == []


def test_key_echo_app_service_starts_and_stops_echo_capture() -> None:
    capture = FakeCapture()
    speech_output = FakeSpeechOutput()
    service = KeyEchoAppService(
        outputs=OutputCapabilities(speech=SpeechService.single_backend(speech_output))
    )
    input_service = KeyboardInputService(capture, service)
    service.attach_input_service(input_service)

    service.start_echo()
    service.stop_echo()

    assert capture.start_calls == 1
    assert capture.stop_calls == 1
    assert service.is_echo_running() is False


def test_key_echo_app_service_exposes_speech_settings_api() -> None:
    speech_output = FakeSpeechOutput()
    service = KeyEchoAppService(
        outputs=OutputCapabilities(speech=SpeechService.single_backend(speech_output))
    )

    assert service.get_speech_backend_options() == (("default", "Default"),)
    assert service.get_selected_speech_backend() == "default"
    service.set_selected_voice("voice-2")
    service.set_rate(120)
    service.set_pitch(3)
    service.set_volume(80)

    assert service.get_selected_voice() == "voice-2"
    assert service.get_rate() == 120
    assert service.get_pitch() == 3
    assert service.get_volume() == 80


def test_build_runtime_composes_local_keyboard_and_speech(monkeypatch) -> None:
    capture = FakeCapture()
    speech_output = FakeSpeechOutput()
    app_calls: list[object] = []

    class FakeQueuedOutputService:
        def __init__(self, *, speech, scheduler) -> None:
            self.speech = speech
            self.scheduler = scheduler

        def speak(self, sequence) -> None:
            self.speech.speak(sequence)

        def cancel(self) -> None:
            self.speech.cancel()

        def pause(self, is_paused: bool) -> None:
            self.speech.pause(is_paused)

        def get_backend_options(self):
            return self.speech.get_backend_options()

        def get_selected_backend(self):
            return self.speech.get_selected_backend()

        def set_backend(self, backend_id):
            self.speech.set_backend(backend_id)

        def list_voices(self):
            return self.speech.list_voices()

        def get_voice(self):
            return self.speech.get_voice()

        def set_voice(self, voice_id):
            self.speech.set_voice(voice_id)

        def get_rate(self):
            return self.speech.get_rate()

        def set_rate(self, value):
            self.speech.set_rate(value)

        def get_pitch(self):
            return self.speech.get_pitch()

        def set_pitch(self, value):
            self.speech.set_pitch(value)

        def get_volume(self):
            return self.speech.get_volume()

        def set_volume(self, value):
            self.speech.set_volume(value)

        def shutdown(self) -> None:
            return None

    class FakeOutputScheduler:
        pass

    class FakeApp:
        def __init__(self, controller) -> None:
            self.controller = controller
            app_calls.append(controller)

    monkeypatch.setattr(main_module, "WindowsKeyboardCapture", lambda: capture)
    monkeypatch.setattr(main_module.sys, "platform", "win32")
    monkeypatch.setattr(
        main_module.Pyttsx3SpeechOutput,
        "load_default",
        classmethod(lambda cls, scheduler=None: speech_output),
    )
    main_module.NvdaControllerSpeechOutput = type(
        "FakeNvdaControllerSpeechOutput",
        (),
        {"load_default": classmethod(lambda cls, scheduler=None: speech_output)},
    )
    monkeypatch.setattr(main_module, "QueuedOutputService", FakeQueuedOutputService)
    monkeypatch.setattr(main_module, "OutputScheduler", FakeOutputScheduler)
    import sys
    import types

    fake_echo_app_module = types.ModuleType("ui.echo.app")
    fake_echo_app_module.EchoApp = FakeApp
    monkeypatch.setitem(sys.modules, "ui.echo.app", fake_echo_app_module)

    runtime = main_module.build_runtime()
    runtime.input_service.bind()

    decision = capture.listener(KeyEvent(vk=66, scan=48, extended=False, pressed=True))

    assert isinstance(runtime.input_service, KeyboardInputService)
    assert isinstance(runtime.app_service, KeyEchoAppService)
    assert runtime.capture is capture
    assert isinstance(runtime.output_scheduler, FakeOutputScheduler)
    assert runtime.speech_service.get_selected_backend() == "pyttsx3"
    assert runtime.output_service.speech is runtime.speech_service
    assert runtime.app is not None
    assert app_calls == [runtime.app_service]
    assert decision == KeyEventDecision.SUPPRESS
    assert speech_output.cancel_calls == 1
    assert speech_output.spoken == [SpeechSequence(items=("VK 66",))]


def test_build_runtime_rejects_non_windows_platform(monkeypatch) -> None:
    monkeypatch.setattr(main_module.sys, "platform", "darwin")

    with pytest.raises(RuntimeError, match="key_echo is currently supported only on Windows"):
        main_module.build_runtime()


def test_main_runs_echo_app_main_loop(monkeypatch) -> None:
    class FakeApp:
        def __init__(self) -> None:
            self.main_loop_calls = 0

        def MainLoop(self) -> int:
            self.main_loop_calls += 1
            return 321

    runtime = main_module.KeyEchoRuntime(
        capture=FakeCapture(),
        output_scheduler=object(),
        speech_service=SpeechService.single_backend(FakeSpeechOutput()),
        output_service=SpeechService.single_backend(FakeSpeechOutput()),
        input_service=KeyboardInputService(FakeCapture(), KeyEchoAppService(outputs=OutputCapabilities(speech=SpeechService.single_backend(FakeSpeechOutput())))),
        app_service=KeyEchoAppService(outputs=OutputCapabilities(speech=SpeechService.single_backend(FakeSpeechOutput()))),
        app=FakeApp(),
    )
    monkeypatch.setattr(main_module, "build_runtime", lambda: runtime)

    result = main_module.main()

    assert result == 321
    assert runtime.app.main_loop_calls == 1


def test_module_executes_main_when_run_as_script(monkeypatch) -> None:
    import pytest

    calls: list[str] = []

    def fake_main() -> int:
        calls.append("main")
        return 654

    monkeypatch.setattr(main_module, "main", fake_main)

    namespace = {"__name__": "__main__", "main": fake_main}
    with pytest.raises(SystemExit) as error:
        exec('if __name__ == "__main__":\n    raise SystemExit(main())\n', namespace)

    assert error.value.code == 654
    assert calls == ["main"]
