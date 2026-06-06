from dataclasses import dataclass
from enum import StrEnum


class ConnectionMode(StrEnum):
    MASTER = "master"
    SLAVE = "slave"


@dataclass(frozen=True, slots=True)
class ConnectionInfo:
    hostname: str
    port: int
    key: str
    mode: ConnectionMode = ConnectionMode.MASTER
    insecure: bool = False
