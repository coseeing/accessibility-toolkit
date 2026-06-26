from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RemoteSessionConnected:
    pass


@dataclass(frozen=True, slots=True)
class RemoteSessionDisconnected:
    pass


@dataclass(frozen=True, slots=True)
class RemoteSessionVersionMismatch:
    pass


@dataclass(frozen=True, slots=True)
class RemotePeerMessageReceived:
    message_type: str
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class RemoteProtocolMessageIgnored:
    message_type: str
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class RemoteProtocolMessageInvalid:
    reason: str
    payload: dict[str, Any]
