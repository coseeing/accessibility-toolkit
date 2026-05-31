from dataclasses import dataclass
from enum import StrEnum


class ConnectionState(StrEnum):
    IDLE = "idle"
    CONNECTED = "connected"


class ControlState(StrEnum):
    IDLE = "idle"
    CONNECTED = "connected"
    CONTROLLING = "controlling"
    SUSPENDED = "suspended"


@dataclass(slots=True)
class RuntimeState:
    connection_state: ConnectionState | str = ConnectionState.IDLE
    control_state: ControlState | str = ControlState.IDLE
