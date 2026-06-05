from dataclasses import dataclass

from adapters.outputs.interfaces import BrailleOutput, ToneOutput
from application.speech_service import SpeechService


@dataclass(frozen=True)
class OutputCapabilities:
    speech: SpeechService
    tone: ToneOutput | None = None
    braille: BrailleOutput | None = None
