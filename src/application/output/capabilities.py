from dataclasses import dataclass

from adapters.outputs.interfaces import BrailleOutput, ToneOutput
from application.output.ports import SpeechServicePort


@dataclass(frozen=True)
class Capabilities:
    speech: SpeechServicePort
    tone: ToneOutput | None = None
    braille: BrailleOutput | None = None
