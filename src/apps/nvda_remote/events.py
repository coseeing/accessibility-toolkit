from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RemoteConnectionChanged:
    state: str


@dataclass(frozen=True, slots=True)
class RemoteControlChanged:
    state: str


@dataclass(frozen=True, slots=True)
class RemoteTransportDisconnected:
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class RemoteMessageReceived:
    type: str
    payload: dict[str, Any]
