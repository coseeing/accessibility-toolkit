from enum import Enum
from typing import Any

from remote_core.serializer import JSONSerializer


class RelayTransport:
    def __init__(self, serializer: JSONSerializer) -> None:
        self.serializer = serializer
        self.connected = False
        self.sent: list[bytes] = []

    def connect(self, hostname: str, port: int, insecure: bool = False) -> None:
        self.connected = True

    def close(self) -> None:
        self.connected = False

    def send(self, message_type: str | Enum, **payload: Any) -> None:
        if not self.connected:
            raise RuntimeError("Transport is not connected")
        self.sent.append(self.serializer.serialize(message_type, **payload))
