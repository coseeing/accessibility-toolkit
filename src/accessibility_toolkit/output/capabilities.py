from dataclasses import dataclass

from accessibility_toolkit.output.interfaces import BrailleOutput, ToneOutput, WaveOutput
from accessibility_toolkit.output.ports import SpeechServicePort


@dataclass(frozen=True)
class Capabilities:
    speech: SpeechServicePort
    tone: ToneOutput | None = None
    braille: BrailleOutput | None = None
    wave: WaveOutput | None = None
