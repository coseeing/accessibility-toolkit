import pytest

from adapters.inputs.base import KeyEventDecision
from application.keyboard import KeyboardInputService
from application.output_capabilities import OutputCapabilities
from application.speech_service import SpeechService
from interop.key import HID, KeyEvent
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


def test_key_echo_app_service_speaks_vk_on_keydown() -> None:
    speech_output = FakeSpeechOutput()
    capture = FakeCapture()
    service = KeyEchoAppService(
        hotkey_capture=FakeHotkeyCapture(),
        input_capture=capture,
        outputs=OutputCapabilities(speech=SpeechService.single_backend(speech_output)),
    )

    input_service = KeyboardInputService(capture, service)
    service.attach_input_service(input_service)
    service.start_echo()

    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)
    decision = service.handle_key_event(event)

    assert decision == KeyEventDecision.SUPPRESS
    assert speech_output.cancel_calls == 1
    assert speech_output.calls == [
        ("cancel", None),
        ("speak", SpeechSequence(items=("HID 0x07:0x04",))),
    ]
    assert speech_output.spoken == [SpeechSequence(items=("HID 0x07:0x04",))]


def test_key_echo_app_service_ignores_keyup_for_speech() -> None:
    speech_output = FakeSpeechOutput()
    capture = FakeCapture()
    service = KeyEchoAppService(
        hotkey_capture=FakeHotkeyCapture(),
        input_capture=capture,
        outputs=OutputCapabilities(speech=SpeechService.single_backend(speech_output)),
    )

    input_service = KeyboardInputService(capture, service)
    service.attach_input_service(input_service)
    service.start_echo()

    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=False)
    decision = service.handle_key_event(event)

    assert decision == KeyEventDecision.SUPPRESS
    assert speech_output.cancel_calls == 0
    assert speech_output.spoken == []


def test_key_echo_app_service_stops_echo_on_escape_keydown() -> None:
    capture = FakeCapture()
    speech_output = FakeSpeechOutput()
    service = KeyEchoAppService(
        hotkey_capture=FakeHotkeyCapture(),
        input_capture=capture,
        outputs=OutputCapabilities(speech=SpeechService.single_backend(speech_output)),
    )
    input_service = KeyboardInputService(capture, service)
    service.attach_input_service(input_service)
    service.start_echo()

    decision = service.handle_key_event(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.ESCAPE, pressed=True)
    )

    assert decision == KeyEventDecision.SUPPRESS
    assert service.is_echo_running() is False
    assert speech_output.cancel_calls == 0
    assert speech_output.spoken == []


def test_key_echo_app_service_starts_and_stops_echo_capture() -> None:
    capture = FakeCapture()
    speech_output = FakeSpeechOutput()
    service = KeyEchoAppService(
        hotkey_capture=FakeHotkeyCapture(),
        input_capture=capture,
        outputs=OutputCapabilities(speech=SpeechService.single_backend(speech_output)),
    )
    input_service = KeyboardInputService(capture, service)
    service.attach_input_service(input_service)

    service.start_echo()
    assert service.is_echo_running() is True
    service.stop_echo()
    assert service.is_echo_running() is False


def test_key_echo_app_service_exposes_speech_settings_api() -> None:
    speech_output = FakeSpeechOutput()
    service = KeyEchoAppService(
        hotkey_capture=FakeHotkeyCapture(),
        input_capture=FakeCapture(),
        outputs=OutputCapabilities(speech=SpeechService.single_backend(speech_output)),
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
    hotkey = FakeHotkeyCapture()
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

    from application.speech_backends import SpeechBackendOption
    monkeypatch.setattr(main_module, "create_input_capture", lambda: capture)
    monkeypatch.setattr(
        main_module,
        "create_hotkey_capture",
        lambda usage=HID.F10: hotkey,
    )
    monkeypatch.setattr(
        main_module,
        "default_speech_backend_options",
        lambda scheduler: (
            SpeechBackendOption(
                backend_id="pyttsx3",
                label="pyttsx3",
                factory=lambda: speech_output,
            ),
        ),
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

    decision = capture.listener(KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.B, pressed=True))

    assert isinstance(runtime.input_service, KeyboardInputService)
    assert isinstance(runtime.app_service, KeyEchoAppService)
    assert runtime.input_capture is capture
    assert runtime.hotkey_capture is hotkey
    assert isinstance(runtime.output_scheduler, FakeOutputScheduler)
    assert runtime.speech_service.get_selected_backend() == "pyttsx3"
    assert runtime.output_service.speech is runtime.speech_service
    assert runtime.app is not None
    assert app_calls == [runtime.app_service]
    assert decision == KeyEventDecision.PASS_THROUGH
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

    class FakeOutputScheduler:
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

    class FakeQueuedOutputService:
        def __init__(self, *, speech, scheduler):
            self.speech = speech
            self.scheduler = scheduler

    class FakeApp:
        def __init__(self, controller):
            self.controller = controller

    from application.speech_backends import SpeechBackendOption
    monkeypatch.setattr(
        main_module,
        "create_input_capture",
        lambda: MacOSFakeCapture(
            manager=FakeManager(permissions=FakePermissions(), backend=object()),
        ),
    )
    monkeypatch.setattr(
        main_module,
        "create_hotkey_capture",
        lambda usage=HID.F10: FakeHotkeyCapture(),
    )
    monkeypatch.setattr(
        main_module,
        "default_speech_backend_options",
        lambda scheduler: (
            SpeechBackendOption(
                backend_id="pyttsx3",
                label="pyttsx3",
                factory=lambda: FakeSpeechOutput(),
            ),
        ),
    )
    monkeypatch.setattr(main_module, "OutputScheduler", FakeOutputScheduler)
    monkeypatch.setattr(main_module, "KeyboardInputService", FakeKeyboardInputService)
    monkeypatch.setattr(main_module, "QueuedOutputService", FakeQueuedOutputService)

    import sys as _sys
    import types
    fake_echo_app_module = types.ModuleType("ui.echo.app")
    fake_echo_app_module.EchoApp = FakeApp
    monkeypatch.setitem(_sys.modules, "ui.echo.app", fake_echo_app_module)

    runtime = main_module.build_runtime()
    assert isinstance(runtime.input_capture, MacOSFakeCapture)
    assert runtime.speech_service.get_selected_backend() == "pyttsx3"
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
        output_scheduler=object(),
        speech_service=SpeechService.single_backend(FakeSpeechOutput()),
        output_service=SpeechService.single_backend(FakeSpeechOutput()),
        input_service=KeyboardInputService(FakeCapture(), KeyEchoAppService(hotkey_capture=FakeHotkeyCapture(), input_capture=FakeCapture(), outputs=OutputCapabilities(speech=SpeechService.single_backend(FakeSpeechOutput())))),
        app_service=KeyEchoAppService(hotkey_capture=FakeHotkeyCapture(), input_capture=FakeCapture(), outputs=OutputCapabilities(speech=SpeechService.single_backend(FakeSpeechOutput()))),
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
        outputs=OutputCapabilities(speech=SpeechService.single_backend(speech_output)),
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
        outputs=OutputCapabilities(speech=SpeechService.single_backend(speech_output)),
    )
    input_service = KeyboardInputService(capture, service)
    service.attach_input_service(input_service)
    service.bind()
    hotkey.start()

    hotkey.handler()
    assert service.is_echo_running() is True

    decision = service.handle_key_event(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.ENTER, pressed=False)
    )

    assert decision == KeyEventDecision.SUPPRESS


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


def test_key_echo_app_service_idle_enter_uses_hotkey_path() -> None:
    capture = FakeCapture()
    hotkey = FakeHotkeyCapture()
    speech_output = FakeSpeechOutput()
    service = KeyEchoAppService(
        hotkey_capture=hotkey,
        input_capture=capture,
        outputs=OutputCapabilities(speech=SpeechService.single_backend(speech_output)),
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
        outputs=OutputCapabilities(speech=SpeechService.single_backend(speech_output)),
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
        outputs=OutputCapabilities(speech=SpeechService.single_backend(speech_output)),
    )
    input_service = KeyboardInputService(capture, service)
    service.attach_input_service(input_service)
    service.bind()
    hotkey.start()
    hotkey.handler()

    decision = service.handle_key_event(KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.ESCAPE, pressed=True))

    assert decision == KeyEventDecision.SUPPRESS
    assert service.is_echo_running() is False
    assert capture.stop_calls == 1
    assert hotkey.start_calls == 2


def test_build_runtime_starts_with_hotkey_running_and_keyboard_stopped(monkeypatch) -> None:
    capture = FakeCapture()
    hotkey = FakeHotkeyCapture()
    speech_output = FakeSpeechOutput()
    requested_hotkeys: list[int] = []

    from application.speech_backends import SpeechBackendOption
    monkeypatch.setattr(main_module, "create_input_capture", lambda: capture)
    monkeypatch.setattr(
        main_module,
        "create_hotkey_capture",
        lambda usage=HID.F10: requested_hotkeys.append(usage) or hotkey,
    )
    monkeypatch.setattr(
        main_module,
        "default_speech_backend_options",
        lambda scheduler: (
            SpeechBackendOption(
                backend_id="pyttsx3",
                label="pyttsx3",
                factory=lambda: speech_output,
            ),
        ),
    )

    import sys as _sys
    import types
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

    from application.speech_backends import SpeechBackendOption
    monkeypatch.setattr(main_module, "create_input_capture", lambda: capture)
    monkeypatch.setattr(
        main_module,
        "create_hotkey_capture",
        lambda usage=HID.F10: requested_hotkeys.append(usage) or hotkey,
    )
    monkeypatch.setattr(
        main_module,
        "default_speech_backend_options",
        lambda scheduler: (
            SpeechBackendOption(
                backend_id="pyttsx3",
                label="pyttsx3",
                factory=lambda: speech_output,
            ),
        ),
    )

    original = main_module.KeyEchoAppFacade.enter_usage
    monkeypatch.setattr(main_module.KeyEchoAppFacade, "enter_usage", HID.F10)

    import sys as _sys
    import types
    fake_echo_app_module = types.ModuleType("ui.echo.app")
    fake_echo_app_module.EchoApp = lambda controller: None
    monkeypatch.setitem(_sys.modules, "ui.echo.app", fake_echo_app_module)

    try:
        main_module.build_runtime()
    finally:
        monkeypatch.setattr(main_module.KeyEchoAppFacade, "enter_usage", original)

    assert requested_hotkeys == [HID.F10]


def test_build_runtime_shutdown_stops_both_captures(monkeypatch) -> None:
    capture = FakeCapture()
    hotkey = FakeHotkeyCapture()
    speech_output = FakeSpeechOutput()
    requested_hotkeys: list[int] = []

    from application.speech_backends import SpeechBackendOption
    monkeypatch.setattr(main_module, "create_input_capture", lambda: capture)
    monkeypatch.setattr(
        main_module,
        "create_hotkey_capture",
        lambda usage=HID.F10: requested_hotkeys.append(usage) or hotkey,
    )
    monkeypatch.setattr(
        main_module,
        "default_speech_backend_options",
        lambda scheduler: (
            SpeechBackendOption(
                backend_id="pyttsx3",
                label="pyttsx3",
                factory=lambda: speech_output,
            ),
        ),
    )

    import sys as _sys
    import types
    fake_echo_app_module = types.ModuleType("ui.echo.app")
    fake_echo_app_module.EchoApp = lambda controller: None
    monkeypatch.setitem(_sys.modules, "ui.echo.app", fake_echo_app_module)

    runtime = main_module.build_runtime()
    runtime.app_service.start_echo()
    runtime.app_service.shutdown()

    assert requested_hotkeys == [HID.F10]
    assert hotkey.running is False
    assert capture.running is False
