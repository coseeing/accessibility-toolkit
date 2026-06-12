from adapters.inputs.base import HotkeyCapture, InputCapture, KeyEventDecision
from application.input import InputActivationUseCase
from application.keyboard import KeyEventHandler, KeyboardInputService
from application.output_capabilities import OutputCapabilities
from interop.key.key_event import KeyEvent

from apps.key_echo.use_cases import (
    KeyEchoControlUseCase,
    KeyEchoInputUseCase,
)
from apps.shared.mode_manager import ModeManager
from apps.shared.speech_settings_controller import SpeechSettingsController


class EchoKeysMode:
    mode_id = "echo_keys"
    enter_hotkey = "enter"
    exit_hotkey = 0x1B

    def __init__(self, control, echo_input):
        self._control = control
        self._echo_input = echo_input

    def can_enter(self) -> bool:
        return True

    def enter(self) -> bool:
        self._control.start_echo()
        return True

    def exit(self) -> bool:
        self._control.stop_echo()
        return True

    def handle_key_event(self, event):
        return self._echo_input.handle(event)


class KeyEchoAppFacade(KeyEventHandler):
    def __init__(
        self,
        *,
        hotkey_capture: HotkeyCapture,
        input_capture: InputCapture,
        outputs: OutputCapabilities,
    ) -> None:
        self.hotkey_capture = hotkey_capture
        self.input_capture = input_capture
        self._outputs = outputs
        self._input_service: KeyboardInputService | None = None
        self._status_listener = None
        self._echo_control: KeyEchoControlUseCase | None = None

        self._echo_input = KeyEchoInputUseCase(
            cancel=lambda: self._outputs.speech.cancel(),
            speak=lambda sequence: self._outputs.speech.speak(sequence),
        )
        self._speech_settings = SpeechSettingsController(
            speech=outputs.speech,
        )
        self._activation = InputActivationUseCase(
            input_capture=input_capture,
            hotkey_capture=hotkey_capture,
            is_active=self.is_echo_running,
            set_active=self._set_echo_active,
            notify_error=lambda message: self._notify_status_listener(
                {"kind": "error", "message": message}
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
            EchoKeysMode(self._echo_control, self._echo_input)
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

    def get_speech_backend_options(self) -> tuple[tuple[str, str], ...]:
        return self._speech_settings.get_backend_options()

    def get_selected_speech_backend(self) -> str:
        return self._speech_settings.get_selected_backend()

    def set_speech_backend(self, backend_id: str) -> None:
        self._speech_settings.set_backend(backend_id)
        self._notify_status_listener(
            {"kind": "speech_backend", "backend_id": backend_id}
        )

    def get_available_voices(self) -> tuple[tuple[str, str], ...]:
        return self._speech_settings.list_voices()

    def get_selected_voice(self) -> str | None:
        return self._speech_settings.get_voice()

    def set_selected_voice(self, voice_id: str) -> None:
        self._speech_settings.set_voice(voice_id)

    def get_rate(self) -> int | None:
        return self._speech_settings.get_rate()

    def set_rate(self, value: int) -> None:
        self._speech_settings.set_rate(value)

    def get_pitch(self) -> int | None:
        return self._speech_settings.get_pitch()

    def set_pitch(self, value: int) -> None:
        self._speech_settings.set_pitch(value)

    def get_volume(self) -> int | None:
        return self._speech_settings.get_volume()

    def set_volume(self, value: int) -> None:
        self._speech_settings.set_volume(value)

    def shutdown(self) -> None:
        self.stop_echo()
        if self._input_service is not None and self._input_service.running:
            self._input_service.stop()
        if self.hotkey_capture is not None and self.hotkey_capture.running:
            self.hotkey_capture.stop()
        self._outputs.speech.shutdown()

    def handle_key_event(self, event: KeyEvent) -> KeyEventDecision:
        return self._mode_manager.handle_key_event(event)

    def _notify_status_listener(self, status: dict[str, str]) -> None:
        if self._status_listener is not None:
            self._status_listener(status)

    def _handle_idle_hotkey(self) -> None:
        if self.is_echo_running():
            return
        self.start_echo()


