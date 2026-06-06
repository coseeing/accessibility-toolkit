from dataclasses import dataclass

from adapters.outputs.interfaces import BrailleOutput, ToneOutput
from application.output_service import SpeechOutputService


@dataclass(frozen=True)
class OutputCapabilities:
    speech: SpeechOutputService
    tone: ToneOutput | None = None
    braille: BrailleOutput | None = None
