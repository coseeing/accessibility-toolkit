from dataclasses import dataclass
from typing import Any


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
