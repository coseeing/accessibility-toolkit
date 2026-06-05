from adapters.inputs.base import KeyEventDecision
from application.keyboard import KeyEventHandler
from application.output_capabilities import OutputCapabilities
from remote_core.models.keys import KeyEvent
from remote_core.models.speech_sequence import SpeechSequence


class KeyEchoAppService(KeyEventHandler):
    def __init__(self, *, outputs: OutputCapabilities) -> None:
        self._outputs = outputs

    def handle_key_event(self, event: KeyEvent) -> KeyEventDecision:
        if event.pressed:
            self._outputs.speech.speak(SpeechSequence(items=(f"VK {event.vk}",)))
        return KeyEventDecision.PASS_THROUGH
