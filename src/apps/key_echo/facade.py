from adapters.inputs.base import KeyEventDecision
from application.keyboard import KeyEventHandler, KeyboardInputService
from application.output_capabilities import OutputCapabilities
from interop.key.key_event import KeyEvent

from apps.key_echo.use_cases import (
    KeyEchoControlUseCase,
    KeyEchoHotkeyAction,
    KeyEchoInputUseCase,
    KeyEchoSpeechSettingsUseCase,
    KeyEchoStateTransitionHotkeyUseCase,
)


class KeyEchoAppFacade(KeyEventHandler):
    def __init__(self, *, outputs: OutputCapabilities) -> None:
        self._outputs = outputs
        self._input_service: KeyboardInputService | None = None
        self._status_listener = None
        self._echo_control: KeyEchoControlUseCase | None = None

        self._state_transition_hotkeys = KeyEchoStateTransitionHotkeyUseCase.default()
        self._echo_input = KeyEchoInputUseCase(
            cancel=lambda: self._outputs.speech.cancel(),
            speak=lambda sequence: self._outputs.speech.speak(sequence),
        )
        self._speech_settings = KeyEchoSpeechSettingsUseCase(
            speech=outputs.speech,
        )

    def attach_input_service(self, input_service: KeyboardInputService) -> None:
        self._input_service = input_service
        self._echo_control = KeyEchoControlUseCase(
            input_service=input_service,
            notify_status=self._notify_status_listener,
        )

    def set_status_listener(self, listener) -> None:
        self._status_listener = listener

    def start_echo(self) -> None:
        if self._echo_control is None:
            raise RuntimeError("Keyboard input service is not attached")
        self._echo_control.start_echo()

    def stop_echo(self) -> None:
        if self._echo_control is None:
            return
        self._echo_control.stop_echo()

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
        self._outputs.speech.shutdown()

    def handle_key_event(self, event: KeyEvent) -> KeyEventDecision:
        action = self._state_transition_hotkeys.match(event)
        if action == KeyEchoHotkeyAction.START_ECHO and not self.is_echo_running():
            self.start_echo()
            return KeyEventDecision.SUPPRESS
        if action == KeyEchoHotkeyAction.STOP_ECHO and self.is_echo_running():
            self.stop_echo()
            return KeyEventDecision.SUPPRESS
        if self.is_echo_running():
            return self._echo_input.handle(event)
        return KeyEventDecision.PASS_THROUGH

    def _notify_status_listener(self, status: dict[str, str]) -> None:
        if self._status_listener is not None:
            self._status_listener(status)
