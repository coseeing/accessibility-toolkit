from accessibility_toolkit.events import AppEvent, ErrorRaised, SpeechEngineChanged
from accessibility_toolkit.input.capture import HotkeyCapture, InputCapture
from accessibility_toolkit.input.events import CapturedKeyEvent
from accessibility_toolkit.input import (
    assemble_pipeline_result,
    InputActivationUseCase,
    KeyboardPipelineResult,
    should_pass_through_system_toggle,
)
from accessibility_toolkit.input import (
    KeyBinding,
    KeyChord,
    KeyEventHandler,
    KeyEventRouter,
    KeyTrigger,
    KeyboardInputService,
)
from accessibility_toolkit.output import Capabilities
from accessibility_toolkit.input import HID

from apps.key_echo.use_cases import (
    KeyEchoControlUseCase,
    KeyEchoInputUseCase,
)
from apps.key_echo.events import EchoStateChanged
from accessibility_toolkit.interaction import ModeManager


class EchoKeysMode:
    mode_id = "echo_keys"
    enter_usage = HID.F10
    def __init__(self, control, echo_input, exit_active):
        self._control = control
        self._echo_input = echo_input
        self.key_router = KeyEventRouter(
            bindings=(
                KeyBinding(
                    chord=KeyChord(usages=frozenset({HID.ESCAPE})),
                    trigger=KeyTrigger.KEY_DOWN,
                    handler=lambda _event: exit_active(),
                ),
            ),
            fallback=echo_input.handle,
        )

    def can_enter(self) -> bool:
        return True

    def enter(self) -> bool:
        self._control.start_echo()
        return True

    def exit(self) -> bool:
        self._control.stop_echo()
        return True

class KeyEchoAppService(KeyEventHandler):
    enter_usage = EchoKeysMode.enter_usage

    def __init__(
        self,
        *,
        hotkey_capture: HotkeyCapture,
        input_capture: InputCapture,
        capabilities: Capabilities,
        main_thread_dispatch=None,
    ) -> None:
        self.hotkey_capture = hotkey_capture
        self.input_capture = input_capture
        self._capabilities = capabilities
        self._input_service: KeyboardInputService | None = None
        self._status_listener = None
        self._echo_control: KeyEchoControlUseCase | None = None
        self._main_thread_dispatch = main_thread_dispatch or (
            lambda callback: callback()
        )

        self._echo_input = KeyEchoInputUseCase(
            cancel=lambda: self._capabilities.speech.cancel(),
            speak=lambda sequence: self._capabilities.speech.speak(sequence),
        )
        self._activation = InputActivationUseCase(
            input_capture=input_capture,
            hotkey_capture=hotkey_capture,
            is_active=self.is_echo_running,
            set_active=self._set_echo_active,
            notify_error=lambda message: self._notify_status_listener(
                ErrorRaised(message)
            ),
        )
        self._mode_manager = ModeManager(
            activation=self._activation,
            notify_status=self._notify_status_listener,
        )

    def attach_input_service(self, input_service: KeyboardInputService) -> None:
        self._input_service = input_service
        self._echo_control = KeyEchoControlUseCase(
            notify_status=self._notify_status_listener,
        )
        self._mode_manager.register(
            EchoKeysMode(
                self._echo_control,
                self._echo_input,
                self._mode_manager.exit_active_mode,
            )
        )

    def bind(self) -> None:
        self.input_capture.set_listener(self.handle_key_event)
        self.hotkey_capture.set_handler(self._handle_idle_hotkey)

    def set_status_listener(self, listener) -> None:
        self._status_listener = listener

    def start_echo(self) -> None:
        if self._echo_control is None:
            raise RuntimeError("Keyboard input service is not attached")
        self._mode_manager.activate_mode("echo_keys")

    def stop_echo(self) -> None:
        if self._echo_control is None:
            return
        if self._mode_manager.active_mode_id == "echo_keys":
            self._mode_manager.exit_active_mode()
        else:
            self._echo_control.stop_echo()

    def _set_echo_active(self, active: bool) -> None:
        if self._echo_control is not None:
            self._echo_control.set_running(active)

    def is_echo_running(self) -> bool:
        if self._echo_control is None:
            return False
        return self._echo_control.is_running()

    def notify_speech_engine_changed(self, engine_id: str) -> None:
        self._notify_status_listener(SpeechEngineChanged(engine_id))

    def shutdown(self) -> None:
        self.stop_echo()
        if self._input_service is not None and self._input_service.running:
            self._input_service.stop()
        if self.hotkey_capture is not None and self.hotkey_capture.running:
            self.hotkey_capture.stop()
        self._capabilities.speech.shutdown()

    def handle_key_event(self, event: CapturedKeyEvent) -> KeyboardPipelineResult:
        send_to_system = should_pass_through_system_toggle(event)
        app_result = self._mode_manager.handle_key_event(event.key_event)
        return assemble_pipeline_result(
            send_to_system=send_to_system, app_result=app_result
        )

    def _notify_status_listener(
        self, status: AppEvent | EchoStateChanged
    ) -> None:
        if self._status_listener is not None:
            self._status_listener(status)

    def _handle_idle_hotkey(self) -> None:
        if self.is_echo_running():
            return
        self._main_thread_dispatch(self.start_echo)
