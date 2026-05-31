from collections.abc import Callable
from enum import Enum
from typing import Any

from remote_core.connection_info import ConnectionInfo
from remote_core.protocol import RemoteMessageType
from remote_core.transport.base import Transport


class RemoteSession:
    PROTOCOL_VERSION = 2

    def __init__(
        self,
        transport: Transport,
        on_status: Callable[[dict[str, Any]], None],
    ) -> None:
        self.transport = transport
        self.on_status = on_status

    def connect(self, connection_info: ConnectionInfo) -> None:
        self.transport.connect(
            connection_info.hostname,
            connection_info.port,
            insecure=connection_info.insecure,
        )
        self.transport.send(
            RemoteMessageType.PROTOCOL_VERSION,
            version=self.PROTOCOL_VERSION,
        )
        self.transport.send(
            RemoteMessageType.JOIN,
            channel=connection_info.key,
            mode=self._mode_value(connection_info.mode),
        )
        self.on_status({"state": "connected"})

    def disconnect(self) -> None:
        self.transport.close()
        self.on_status({"state": "idle"})

    def _mode_value(self, mode: str | Enum) -> str:
        if isinstance(mode, Enum):
            return str(mode.value)
        return mode
