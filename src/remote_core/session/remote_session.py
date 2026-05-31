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

    def disconnect(self) -> None:
        self.transport.close()
        self.on_status({"kind": "connection", "state": "idle"})

    def handle_message(self, payload: dict[str, Any]) -> bool:
        match payload.get("type"):
            case RemoteMessageType.CHANNEL_JOINED.value:
                self.on_status({"kind": "connection", "state": "connected"})
                return True
            case RemoteMessageType.VERSION_MISMATCH.value:
                self.on_status(
                    {"kind": "connection", "state": "version_mismatch"}
                )
                return True
            case (
                RemoteMessageType.MOTD.value
                | RemoteMessageType.CLIENT_JOINED.value
                | RemoteMessageType.CLIENT_LEFT.value
                | RemoteMessageType.ERROR.value
            ):
                self.on_status(
                    {
                        "kind": "remote",
                        "type": payload.get("type"),
                        "payload": payload,
                    }
                )
                return True
            case RemoteMessageType.PING.value:
                return True
            case _:
                return False

    def _mode_value(self, mode: str | Enum) -> str:
        if isinstance(mode, Enum):
            return str(mode.value)
        return mode
