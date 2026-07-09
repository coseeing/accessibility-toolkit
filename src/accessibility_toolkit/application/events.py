from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ErrorRaised:
    message: str


@dataclass(frozen=True, slots=True)
class SpeechEngineChanged:
    engine_id: str


@dataclass(frozen=True, slots=True)
class InputCaptureChanged:
    active: bool


@dataclass(frozen=True, slots=True)
class HotkeyCaptureChanged:
    active: bool


@dataclass(frozen=True, slots=True)
class ClipboardAvailabilityChanged:
    available: bool


@dataclass(frozen=True, slots=True)
class ModeChanged:
    mode_id: str
    active: bool


AppEvent = (
    ErrorRaised
    | SpeechEngineChanged
    | InputCaptureChanged
    | HotkeyCaptureChanged
    | ClipboardAvailabilityChanged
    | ModeChanged
)
