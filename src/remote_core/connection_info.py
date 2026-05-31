from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConnectionInfo:
    hostname: str
    port: int
    key: str
    mode: str = "leader"
    insecure: bool = False
