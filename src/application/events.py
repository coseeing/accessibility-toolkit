from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ErrorRaised:
    message: str


@dataclass(frozen=True, slots=True)
class SpeechBackendChanged:
    backend_id: str


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
    | SpeechBackendChanged
    | InputCaptureChanged
    | HotkeyCaptureChanged
    | ClipboardAvailabilityChanged
    | ModeChanged
)


@dataclass(frozen=True, slots=True)
class StatusEvent:
    kind: str
    state: str | None = None
    type: str | None = None
    reason: str | None = None
    payload: dict[str, Any] | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "StatusEvent":
        return cls(
            kind=str(payload.get("kind", "")),
            state=payload.get("state"),
            type=payload.get("type"),
            reason=payload.get("reason"),
            payload=payload.get("payload"),
        )
