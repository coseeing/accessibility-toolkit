from adapters.inputs.base import KeyEventDecision
from application.keyboard import KeyEventHandler, KeyboardInputService
from application.output_capabilities import OutputCapabilities
from interop.key.key_event import KeyEvent
from interop.speech.speech_sequence import SpeechSequence


class KeyEchoAppService(KeyEventHandler):
    _LOCAL_STOP_VK = 0x1B

    def __init__(self, *, outputs: OutputCapabilities) -> None:
        self._outputs = outputs
        self._input_service: KeyboardInputService | None = None
        self._status_listener = None

    def attach_input_service(self, input_service: KeyboardInputService) -> None:
        self._input_service = input_service

    def set_status_listener(self, listener) -> None:
        self._status_listener = listener

    def start_echo(self) -> None:
        if self._input_service is None:
            raise RuntimeError("Keyboard input service is not attached")
        if not self._input_service.running:
            self._input_service.start()
        self._notify_status_listener({"kind": "echo", "state": "running"})

    def stop_echo(self) -> None:
        if self._input_service is None:
            return
        if self._input_service.running:
            self._input_service.stop()
        self._notify_status_listener({"kind": "echo", "state": "stopped"})

    def is_echo_running(self) -> bool:
        return self._input_service is not None and self._input_service.running

    def get_speech_backend_options(self) -> tuple[tuple[str, str], ...]:
        return self._outputs.speech.get_backend_options()

    def get_selected_speech_backend(self) -> str:
        return self._outputs.speech.get_selected_backend()

    def set_speech_backend(self, backend_id: str) -> None:
        self._outputs.speech.set_backend(backend_id)
        self._notify_status_listener({"kind": "speech_backend", "backend_id": backend_id})

    def get_available_voices(self) -> tuple[tuple[str, str], ...]:
        return self._outputs.speech.list_voices()

    def get_selected_voice(self) -> str | None:
        return self._outputs.speech.get_voice()

    def set_selected_voice(self, voice_id: str) -> None:
        self._outputs.speech.set_voice(voice_id)

    def get_rate(self) -> int | None:
        return self._outputs.speech.get_rate()

    def set_rate(self, value: int) -> None:
        self._outputs.speech.set_rate(value)

    def get_pitch(self) -> int | None:
        return self._outputs.speech.get_pitch()

    def set_pitch(self, value: int) -> None:
        self._outputs.speech.set_pitch(value)

    def get_volume(self) -> int | None:
        return self._outputs.speech.get_volume()

    def set_volume(self, value: int) -> None:
        self._outputs.speech.set_volume(value)

    def shutdown(self) -> None:
        self.stop_echo()
        self._outputs.speech.shutdown()

    def handle_key_event(self, event: KeyEvent) -> KeyEventDecision:
        if event.vk == self._LOCAL_STOP_VK:
            if event.pressed:
                self.stop_echo()
            return KeyEventDecision.SUPPRESS
        if event.pressed:
            self._outputs.speech.cancel()
            speech = SpeechSequence(items=(f"VK {event.vk}",))
            self._outputs.speech.speak(speech)
        return KeyEventDecision.SUPPRESS

    def _notify_status_listener(self, status: dict[str, str]) -> None:
        if self._status_listener is not None:
            self._status_listener(status)
