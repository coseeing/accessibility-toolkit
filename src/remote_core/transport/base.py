from enum import Enum
from typing import Any, Protocol


class Transport(Protocol):
    def connect(self, hostname: str, port: int, insecure: bool = False) -> None: ...

    def close(self) -> None: ...

    def send(self, message_type: str | Enum, **payload: Any) -> None: ...
