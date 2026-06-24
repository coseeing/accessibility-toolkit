from dataclasses import dataclass
from typing import Any


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


@dataclass(frozen=True, slots=True)
class StatusEvent:
    kind: str
    state: str | None = None
    type: str | None = None
    reason: str | None = None
    payload: dict[str, Any] | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "StatusEvent":
        def optional_string(value: Any) -> str | None:
            if value is None:
                return None
            return str(value)

        payload_value = payload.get("payload")
        return cls(
            kind=str(payload.get("kind", "")),
            state=optional_string(payload.get("state")),
            type=optional_string(payload.get("type")),
            reason=optional_string(payload.get("reason")),
            payload=payload_value if isinstance(payload_value, dict) else None,
        )
