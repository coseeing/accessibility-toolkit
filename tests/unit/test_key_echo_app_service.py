import pytest
import types

from adapters.inputs.captured_event import CapturedKeyEvent
from adapters.windows.native_key_context import WindowsNativeKeyContext
from application.input.results import AppKeyEventResult, KeyboardPipelineResult
from application.events import ErrorRaised, ModeChanged, SpeechEngineChanged
from application.keyboard import KeyboardInputService
from application.output import Capabilities
from application.output.speech import SpeechService
from interop.key import HID, KeyEvent
from interop.speech.speech_sequence import SpeechSequence

from apps.key_echo.events import EchoStateChanged
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

    def get_engine_options(self) -> tuple[tuple[str, str], ...]:
        return (("default", "Default"),)

    def get_selected_engine(self) -> str:
        return "default"

    def set_engine(self, engine_id: str) -> None:
        del engine_id

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


class FakeHotkeyCapture:
    def __init__(self) -> None:
        self.handler = None
        self.start_calls = 0
        self.stop_calls = 0

    def set_handler(self, handler) -> None:
        self.handler = handler

    def start(self) -> None:
        self.start_calls += 1

    def stop(self) -> None:
        self.stop_calls += 1

    @property
    def running(self) -> bool:
        return self.start_calls > self.stop_calls


class FakeRuntimeSpeech:
    def __init__(self, output: FakeSpeechOutput) -> None:
        self.output = output

    def speak(self, sequence) -> None:
        self.output.speak(sequence)

    def cancel(self) -> None:
        self.output.cancel()

    def pause(self, is_paused: bool) -> None:
        self.output.pause(is_paused)

    def get_engine_options(self):
        return (("pyttsx3", "pyttsx3"),)

    def get_selected_engine(self):
        return "pyttsx3"

    def set_engine(self, engine_id):
        del engine_id

    def list_voices(self):
        return self.output.list_voices()

    def get_voice(self):
        return self.output.get_voice()

    def set_voice(self, voice_id):
        self.output.set_voice(voice_id)

    def get_rate(self):
        return self.output.get_rate()

    def set_rate(self, value):
        self.output.set_rate(value)

    def get_pitch(self):
        return self.output.get_pitch()

    def set_pitch(self, value):
        self.output.set_pitch(value)

    def get_volume(self):
        return self.output.get_volume()

    def set_volume(self, value):
        self.output.set_volume(value)

    def shutdown(self) -> None:
        return None


class FakeRuntimeSpeaker(FakeRuntimeSpeech):
    def __init__(self, speech: FakeRuntimeSpeech) -> None:
        self.speech = speech
        self.output = speech.output


def install_fake_key_echo_runtime_parts(
    monkeypatch,
    *,
    capture,
    hotkey,
    speech_output,
    requested_hotkeys: list[int] | None = None,
    scheduler=None,
) -> object:
    scheduler = scheduler if scheduler is not None else object()
    speech = FakeRuntimeSpeech(speech_output)
    speaker = FakeRuntimeSpeaker(speech)

    def fake_build_app_runtime_parts(
        *,
        hotkey_usage,
        selected_backend_id,
        fallback_backend_id,
        include_tone,
        **kwargs,
    ):
        assert selected_backend_id == "pyttsx3"
        assert fallback_backend_id == "pyttsx3"
        assert include_tone is False
        assert kwargs == {}
        if requested_hotkeys is not None:
            requested_hotkeys.append(hotkey_usage)
        return types.SimpleNamespace(
            input_capture=capture,
            hotkey_capture=hotkey,
            clipboard=None,
            tone_output=None,
            output=types.SimpleNamespace(
                scheduler=scheduler,
                speech=speech,
                speaker=speaker,
                capabilities=Capabilities(speech=speaker),
            ),
        )

    monkeypatch.setattr(
        main_module,
        "build_app_runtime_parts",
        fake_build_app_runtime_parts,
    )
    return scheduler


def test_key_echo_app_service_speaks_vk_on_keydown() -> None:
    speech_output = FakeSpeechOutput()
    capture = FakeCapture()
    service = KeyEchoAppService(
        hotkey_capture=FakeHotkeyCapture(),
        input_capture=capture,
        capabilities=Capabilities(speech=SpeechService.single_backend(speech_output)),
    )

    input_service = KeyboardInputService(capture, service)
    service.attach_input_service(input_service)
    service.start_echo()

    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)
    decision = service.handle_key_event(CapturedKeyEvent(key_event=event, native_context=None))

    assert decision == KeyboardPipelineResult(send_to_system=False, app_result=AppKeyEventResult.HANDLED_STOP)
    assert speech_output.cancel_calls == 1
    assert speech_output.calls == [
        ("cancel", None),
        ("speak", SpeechSequence(items=("HID 0x07:0x04",))),
    ]
    assert speech_output.spoken == [SpeechSequence(items=("HID 0x07:0x04",))]


def test_key_echo_app_service_speaks_right_shift_on_keydown() -> None:
    speech_output = FakeSpeechOutput()
    capture = FakeCapture()
    service = KeyEchoAppService(
        hotkey_capture=FakeHotkeyCapture(),
        input_capture=capture,
        capabilities=Capabilities(speech=SpeechService.single_backend(speech_output)),
    )

    input_service = KeyboardInputService(capture, service)
    service.attach_input_service(input_service)
    service.start_echo()

    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.RIGHT_SHIFT, pressed=True)
    decision = service.handle_key_event(CapturedKeyEvent(key_event=event, native_context=None))

    assert decision == KeyboardPipelineResult(send_to_system=False, app_result=AppKeyEventResult.HANDLED_STOP)
    assert speech_output.cancel_calls == 1
    assert speech_output.calls == [
        ("cancel", None),
        ("speak", SpeechSequence(items=("HID 0x07:0xE5",))),
    ]
    assert speech_output.spoken == [SpeechSequence(items=("HID 0x07:0xE5",))]


def test_key_echo_app_service_ignores_keyup_for_speech() -> None:
    speech_output = FakeSpeechOutput()
    capture = FakeCapture()
    service = KeyEchoAppService(
        hotkey_capture=FakeHotkeyCapture(),
        input_capture=capture,
        capabilities=Capabilities(speech=SpeechService.single_backend(speech_output)),
    )

    input_service = KeyboardInputService(capture, service)
    service.attach_input_service(input_service)
    service.start_echo()

    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=False)
    decision = service.handle_key_event(CapturedKeyEvent(key_event=event, native_context=None))

    assert decision == KeyboardPipelineResult(send_to_system=False, app_result=AppKeyEventResult.HANDLED_STOP)
    assert speech_output.cancel_calls == 0
    assert speech_output.spoken == []


def test_key_echo_app_service_stops_echo_on_escape_keydown() -> None:
    capture = FakeCapture()
    speech_output = FakeSpeechOutput()
    service = KeyEchoAppService(
        hotkey_capture=FakeHotkeyCapture(),
        input_capture=capture,
        capabilities=Capabilities(speech=SpeechService.single_backend(speech_output)),
    )
    input_service = KeyboardInputService(capture, service)
    service.attach_input_service(input_service)
    service.start_echo()

    decision = service.handle_key_event(
        CapturedKeyEvent(key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.ESCAPE, pressed=True), native_context=None)
    )

    assert decision == KeyboardPipelineResult(send_to_system=False, app_result=AppKeyEventResult.HANDLED_STOP)
    assert service.is_echo_running() is False
    assert speech_output.cancel_calls == 0
    assert speech_output.spoken == []


def test_key_echo_app_service_passes_num_lock_through_for_windows_captured_event() -> None:
    capture = FakeCapture()
    speech_output = FakeSpeechOutput()
    service = KeyEchoAppService(
        hotkey_capture=FakeHotkeyCapture(),
        input_capture=capture,
        capabilities=Capabilities(speech=SpeechService.single_backend(speech_output)),
    )
    input_service = KeyboardInputService(capture, service)
    service.attach_input_service(input_service)
    service.start_echo()

    decision = service.handle_key_event(
        CapturedKeyEvent(
            key_event=KeyEvent(
                usage_page=HID.KEYBOARD_PAGE,
                usage=HID.NUM_LOCK,
                pressed=True,
            ),
            native_context=WindowsNativeKeyContext(vk_code=0x90, scan_code=69, extended=True),
        )
    )

    assert decision == KeyboardPipelineResult(
        send_to_system=True, app_result=AppKeyEventResult.HANDLED_CONTINUE
    )
    assert speech_output.cancel_calls == 1
    assert speech_output.calls == [
        ("cancel", None),
        ("speak", SpeechSequence(items=("HID 0x07:0x53",))),
    ]


def test_key_echo_app_service_starts_and_stops_echo_capture() -> None:
    capture = FakeCapture()
    speech_output = FakeSpeechOutput()
    service = KeyEchoAppService(
        hotkey_capture=FakeHotkeyCapture(),
        input_capture=capture,
        capabilities=Capabilities(speech=SpeechService.single_backend(speech_output)),
    )
    input_service = KeyboardInputService(capture, service)
    service.attach_input_service(input_service)

    service.start_echo()
    assert service.is_echo_running() is True
    service.stop_echo()
    assert service.is_echo_running() is False


def test_key_echo_app_service_dispatches_typed_echo_state_notifications() -> None:
    capture = FakeCapture()
    delivered = []
    service = KeyEchoAppService(
        hotkey_capture=FakeHotkeyCapture(),
        input_capture=capture,
        capabilities=Capabilities(speech=SpeechService.single_backend(FakeSpeechOutput())),
    )
    input_service = KeyboardInputService(capture, service)
    service.attach_input_service(input_service)
    service.set_status_listener(delivered.append)

    service.start_echo()
    service.stop_echo()

    assert delivered == [
        EchoStateChanged(running=True),
        ModeChanged("echo_keys", active=True),
        EchoStateChanged(running=False),
        ModeChanged("echo_keys", active=False),
    ]


def test_key_echo_app_service_exposes_speech_settings_api() -> None:
    speech_output = FakeSpeechOutput()
    service = KeyEchoAppService(
        hotkey_capture=FakeHotkeyCapture(),
        input_capture=FakeCapture(),
        capabilities=Capabilities(speech=SpeechService.single_backend(speech_output)),
    )

    assert service.get_speech_engine_options() == (("default", "Default"),)
    assert service.get_selected_speech_engine() == "default"
    service.set_selected_voice("voice-2")
    service.set_rate(120)
    service.set_pitch(3)
    service.set_volume(80)

    assert service.get_selected_voice() == "voice-2"
    assert service.get_rate() == 120
    assert service.get_pitch() == 3
    assert service.get_volume() == 80


def test_key_echo_app_service_dispatches_typed_speech_engine_notification() -> None:
    speech_output = FakeSpeechOutput()
    delivered = []
    service = KeyEchoAppService(
        hotkey_capture=FakeHotkeyCapture(),
        input_capture=FakeCapture(),
        capabilities=Capabilities(speech=SpeechService.single_backend(speech_output)),
    )
    service.set_status_listener(delivered.append)

    service.set_speech_engine("default")

    assert delivered == [SpeechEngineChanged("default")]


def test_key_echo_app_service_dispatches_typed_error_notification() -> None:
    class FailingCapture(FakeCapture):
        def start(self) -> None:
            raise RuntimeError("input busy")

    delivered = []
    hotkey = FakeHotkeyCapture()
    service = KeyEchoAppService(
        hotkey_capture=hotkey,
        input_capture=FailingCapture(),
        capabilities=Capabilities(speech=SpeechService.single_backend(FakeSpeechOutput())),
    )
    input_service = KeyboardInputService(service.input_capture, service)
    service.attach_input_service(input_service)
    service.set_status_listener(delivered.append)
    hotkey.start()

    service.start_echo()

    assert delivered == [ErrorRaised("input busy")]


def test_build_runtime_composes_local_keyboard_and_speech(monkeypatch) -> None:
    capture = FakeCapture()
    hotkey = FakeHotkeyCapture()
    speech_output = FakeSpeechOutput()
    app_calls: list[object] = []

    class FakeQueuedService:
        def __init__(self, *, speech) -> None:
            self.speech = speech

        def speak(self, sequence) -> None:
            self.speech.speak(sequence)

        def cancel(self) -> None:
            self.speech.cancel()

        def pause(self, is_paused: bool) -> None:
            self.speech.pause(is_paused)

        def get_engine_options(self):
            return self.speech.get_engine_options()

        def get_selected_engine(self):
            return self.speech.get_selected_engine()

        def set_engine(self, engine_id):
            self.speech.set_engine(engine_id)

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

    class FakeScheduler:
        pass

    class FakeApp:
        def __init__(self, controller) -> None:
            self.controller = controller
            app_calls.append(controller)

    scheduler = install_fake_key_echo_runtime_parts(
        monkeypatch,
        capture=capture,
        hotkey=hotkey,
        speech_output=speech_output,
        scheduler=FakeScheduler(),
    )
    import sys

    fake_echo_app_module = types.ModuleType("ui.echo.app")
    fake_echo_app_module.EchoApp = FakeApp
    monkeypatch.setitem(sys.modules, "ui.echo.app", fake_echo_app_module)

    runtime = main_module.build_runtime()
    runtime.input_service.bind()

    decision = capture.listener(CapturedKeyEvent(key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.B, pressed=True), native_context=None))

    assert isinstance(runtime.input_service, KeyboardInputService)
    assert isinstance(runtime.app_service, KeyEchoAppService)
    assert runtime.input_capture is capture
    assert runtime.hotkey_capture is hotkey
    assert runtime.scheduler is scheduler
    assert runtime.speech.get_selected_engine() == "pyttsx3"
    assert runtime.speaker.speech is runtime.speech
    assert runtime.app is not None
    assert app_calls == [runtime.app_service]
    assert decision == KeyboardPipelineResult(
        send_to_system=False, app_result=AppKeyEventResult.UNHANDLED
    )
    assert speech_output.cancel_calls == 0
    assert speech_output.spoken == []


def test_build_runtime_macos_path_composes_capture(monkeypatch) -> None:
    class MacOSFakeCapture:
        def __init__(self, *, manager):
            self.manager = manager
            self.listener = None
            self.start_calls = 0
            self.stop_calls = 0

        def set_listener(self, listener):
            self.listener = listener

        def start(self):
            self.start_calls += 1

        def stop(self):
            self.stop_calls += 1

        @property
        def running(self):
            return self.start_calls > self.stop_calls

    class FakePermissions:
        @classmethod
        def load_default(cls):
            return cls()

        def is_trusted(self, *, prompt=False):
            return True

        def has_listen_event_access(self, *, prompt=False):
            return True

    class FakeManager:
        def __init__(self, *, permissions, backend):
            self.permissions = permissions
            self.backend = backend

    class FakeScheduler:
        pass

    class FakeKeyboardInputService:
        def __init__(self, capture, handler):
            self._capture = capture
            self.handler = handler

        def bind(self):
            pass

        def start(self):
            pass

        def stop(self):
            pass

        @property
        def running(self):
            return True

    class FakeQueuedService:
        def __init__(self, *, speech):
            self.speech = speech

    class FakeApp:
        def __init__(self, controller):
            self.controller = controller

    capture = MacOSFakeCapture(
        manager=FakeManager(permissions=FakePermissions(), backend=object()),
    )
    install_fake_key_echo_runtime_parts(
        monkeypatch,
        capture=capture,
        hotkey=FakeHotkeyCapture(),
        speech_output=FakeSpeechOutput(),
        scheduler=FakeScheduler(),
    )
    monkeypatch.setattr(main_module, "KeyboardInputService", FakeKeyboardInputService)

    import sys as _sys
    fake_echo_app_module = types.ModuleType("ui.echo.app")
    fake_echo_app_module.EchoApp = FakeApp
    monkeypatch.setitem(_sys.modules, "ui.echo.app", fake_echo_app_module)

    runtime = main_module.build_runtime()
    assert isinstance(runtime.input_capture, MacOSFakeCapture)
    assert runtime.speech.get_selected_engine() == "pyttsx3"
    assert runtime.input_capture.manager is not None


def test_main_runs_echo_app_main_loop(monkeypatch) -> None:
    class FakeApp:
        def __init__(self) -> None:
            self.main_loop_calls = 0

        def MainLoop(self) -> int:
            self.main_loop_calls += 1
            return 321

    runtime = main_module.KeyEchoRuntime(
        input_capture=FakeCapture(),
        hotkey_capture=FakeHotkeyCapture(),
        scheduler=object(),
        speech=SpeechService.single_backend(FakeSpeechOutput()),
        speaker=SpeechService.single_backend(FakeSpeechOutput()),
        input_service=KeyboardInputService(FakeCapture(), KeyEchoAppService(hotkey_capture=FakeHotkeyCapture(), input_capture=FakeCapture(), capabilities=Capabilities(speech=SpeechService.single_backend(FakeSpeechOutput())))),
        app_service=KeyEchoAppService(hotkey_capture=FakeHotkeyCapture(), input_capture=FakeCapture(), capabilities=Capabilities(speech=SpeechService.single_backend(FakeSpeechOutput()))),
        app=FakeApp(),
    )
    monkeypatch.setattr(main_module, "build_runtime", lambda: runtime)

    result = main_module.main()

    assert result == 321
    assert runtime.app.main_loop_calls == 1


def test_key_echo_app_service_starts_echo_on_enter_keydown() -> None:
    capture = FakeCapture()
    hotkey = FakeHotkeyCapture()
    speech_output = FakeSpeechOutput()
    service = KeyEchoAppService(
        hotkey_capture=hotkey,
        input_capture=capture,
        capabilities=Capabilities(speech=SpeechService.single_backend(speech_output)),
    )
    input_service = KeyboardInputService(capture, service)
    service.attach_input_service(input_service)
    service.bind()
    hotkey.start()

    hotkey.handler()

    assert service.is_echo_running() is True
    assert speech_output.spoken == []


def test_key_echo_app_service_enter_keyup_does_not_duplicate_start() -> None:
    capture = FakeCapture()
    hotkey = FakeHotkeyCapture()
    speech_output = FakeSpeechOutput()
    service = KeyEchoAppService(
        hotkey_capture=hotkey,
        input_capture=capture,
        capabilities=Capabilities(speech=SpeechService.single_backend(speech_output)),
    )
    input_service = KeyboardInputService(capture, service)
    service.attach_input_service(input_service)
    service.bind()
    hotkey.start()

    hotkey.handler()
    assert service.is_echo_running() is True

    decision = service.handle_key_event(
        CapturedKeyEvent(key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.ENTER, pressed=False), native_context=None)
    )

    assert decision == KeyboardPipelineResult(send_to_system=False, app_result=AppKeyEventResult.HANDLED_STOP)


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


def test_key_echo_main_configures_logging_before_building_runtime(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class FakeApp:
        def MainLoop(self) -> int:
            calls.append(("mainloop", None))
            return 321

    class FakeRuntime:
        app = FakeApp()

    monkeypatch.setattr(
        main_module,
        "configure_logging",
        lambda app_name="": calls.append(("configure_logging", app_name)),
    )
    monkeypatch.setattr(
        main_module,
        "build_runtime",
        lambda: calls.append(("build_runtime", None)) or FakeRuntime(),
    )

    result = main_module.main()

    assert result == 321
    assert calls == [
        ("configure_logging", "key_echo"),
        ("build_runtime", None),
        ("mainloop", None),
    ]


def test_key_echo_app_service_idle_enter_uses_hotkey_path() -> None:
    capture = FakeCapture()
    hotkey = FakeHotkeyCapture()
    speech_output = FakeSpeechOutput()
    service = KeyEchoAppService(
        hotkey_capture=hotkey,
        input_capture=capture,
        capabilities=Capabilities(speech=SpeechService.single_backend(speech_output)),
    )
    input_service = KeyboardInputService(capture, service)
    service.attach_input_service(input_service)
    service.bind()
    hotkey.start()

    hotkey.handler()

    assert service.is_echo_running() is True
    assert hotkey.stop_calls == 1
    assert capture.start_calls == 1


def test_key_echo_app_service_idle_hotkey_dispatches_start_to_main_thread() -> None:
    capture = FakeCapture()
    hotkey = FakeHotkeyCapture()
    speech_output = FakeSpeechOutput()
    pending = []
    service = KeyEchoAppService(
        hotkey_capture=hotkey,
        input_capture=capture,
        capabilities=Capabilities(speech=SpeechService.single_backend(speech_output)),
        main_thread_dispatch=pending.append,
    )
    input_service = KeyboardInputService(capture, service)
    service.attach_input_service(input_service)
    service.bind()
    hotkey.start()

    hotkey.handler()

    assert service.is_echo_running() is False
    assert len(pending) == 1

    pending.pop()()

    assert service.is_echo_running() is True
    assert hotkey.stop_calls == 1
    assert capture.start_calls == 1


def test_key_echo_app_service_active_escape_exits_through_keyboard_pipeline() -> None:
    capture = FakeCapture()
    hotkey = FakeHotkeyCapture()
    speech_output = FakeSpeechOutput()
    service = KeyEchoAppService(
        hotkey_capture=hotkey,
        input_capture=capture,
        capabilities=Capabilities(speech=SpeechService.single_backend(speech_output)),
    )
    input_service = KeyboardInputService(capture, service)
    service.attach_input_service(input_service)
    service.bind()
    hotkey.start()
    hotkey.handler()

    decision = service.handle_key_event(CapturedKeyEvent(key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.ESCAPE, pressed=True), native_context=None))

    assert decision == KeyboardPipelineResult(send_to_system=False, app_result=AppKeyEventResult.HANDLED_STOP)
    assert service.is_echo_running() is False
    assert capture.stop_calls == 1
    assert hotkey.start_calls == 2


def test_build_runtime_starts_with_hotkey_running_and_keyboard_stopped(monkeypatch) -> None:
    capture = FakeCapture()
    hotkey = FakeHotkeyCapture()
    speech_output = FakeSpeechOutput()
    requested_hotkeys: list[int] = []

    install_fake_key_echo_runtime_parts(
        monkeypatch,
        capture=capture,
        hotkey=hotkey,
        speech_output=speech_output,
        requested_hotkeys=requested_hotkeys,
    )

    import sys as _sys
    fake_echo_app_module = types.ModuleType("ui.echo.app")
    fake_echo_app_module.EchoApp = lambda controller: None
    monkeypatch.setitem(_sys.modules, "ui.echo.app", fake_echo_app_module)

    runtime = main_module.build_runtime()

    assert requested_hotkeys == [HID.F10]
    assert hotkey.running is True
    assert capture.running is False


def test_build_runtime_uses_echo_mode_enter_hotkey_as_single_source_of_truth(monkeypatch) -> None:
    capture = FakeCapture()
    hotkey = FakeHotkeyCapture()
    speech_output = FakeSpeechOutput()
    requested_hotkeys: list[int] = []

    install_fake_key_echo_runtime_parts(
        monkeypatch,
        capture=capture,
        hotkey=hotkey,
        speech_output=speech_output,
        requested_hotkeys=requested_hotkeys,
    )

    original = main_module.KeyEchoAppService.enter_usage
    monkeypatch.setattr(main_module.KeyEchoAppService, "enter_usage", HID.F10)

    import sys as _sys
    fake_echo_app_module = types.ModuleType("ui.echo.app")
    fake_echo_app_module.EchoApp = lambda controller: None
    monkeypatch.setitem(_sys.modules, "ui.echo.app", fake_echo_app_module)

    try:
        main_module.build_runtime()
    finally:
        monkeypatch.setattr(main_module.KeyEchoAppService, "enter_usage", original)

    assert requested_hotkeys == [HID.F10]


def test_build_runtime_shutdown_stops_both_captures(monkeypatch) -> None:
    capture = FakeCapture()
    hotkey = FakeHotkeyCapture()
    speech_output = FakeSpeechOutput()
    requested_hotkeys: list[int] = []

    install_fake_key_echo_runtime_parts(
        monkeypatch,
        capture=capture,
        hotkey=hotkey,
        speech_output=speech_output,
        requested_hotkeys=requested_hotkeys,
    )

    import sys as _sys
    fake_echo_app_module = types.ModuleType("ui.echo.app")
    fake_echo_app_module.EchoApp = lambda controller: None
    monkeypatch.setitem(_sys.modules, "ui.echo.app", fake_echo_app_module)

    runtime = main_module.build_runtime()
    runtime.app_service.start_echo()
    runtime.app_service.shutdown()

    assert requested_hotkeys == [HID.F10]
    assert hotkey.running is False
    assert capture.running is False


def test_key_echo_app_service_returns_pipeline_result_for_regular_key():
    speech_output = FakeSpeechOutput()
    capture = FakeCapture()
    service = KeyEchoAppService(
        hotkey_capture=FakeHotkeyCapture(),
        input_capture=capture,
        capabilities=Capabilities(speech=SpeechService.single_backend(speech_output)),
    )
    input_service = KeyboardInputService(capture, service)
    service.attach_input_service(input_service)
    service.start_echo()

    result = service.handle_key_event(
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True),
            native_context=None,
        )
    )

    assert result == KeyboardPipelineResult(
        send_to_system=False,
        app_result=AppKeyEventResult.HANDLED_STOP,
    )


def test_key_echo_app_service_returns_pipeline_result_for_windows_num_lock():
    speech_output = FakeSpeechOutput()
    capture = FakeCapture()
    service = KeyEchoAppService(
        hotkey_capture=FakeHotkeyCapture(),
        input_capture=capture,
        capabilities=Capabilities(speech=SpeechService.single_backend(speech_output)),
    )
    input_service = KeyboardInputService(capture, service)
    service.attach_input_service(input_service)
    service.start_echo()

    result = service.handle_key_event(
        CapturedKeyEvent(
            key_event=KeyEvent(
                usage_page=HID.KEYBOARD_PAGE,
                usage=HID.NUM_LOCK,
                pressed=True,
            ),
            native_context=WindowsNativeKeyContext(vk_code=0x90, scan_code=69, extended=True),
        )
    )

    assert result == KeyboardPipelineResult(
        send_to_system=True,
        app_result=AppKeyEventResult.HANDLED_CONTINUE,
    )
