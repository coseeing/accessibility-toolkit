from dataclasses import dataclass

from adapters.outputs.interfaces import BrailleOutput, ToneOutput
from application.output.service import SpeechServiceProtocol


@dataclass(frozen=True)
class Capabilities:
    speech: SpeechServiceProtocol
    tone: ToneOutput | None = None
    braille: BrailleOutput | None = None
