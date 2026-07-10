from collections.abc import Callable
from enum import Enum
from typing import Any

from accessibility_toolkit.remote.connection import ConnectionInfo
from accessibility_toolkit.remote.events import (
    RemotePeerMessageReceived,
    RemoteSessionConnected,
    RemoteSessionDisconnected,
    RemoteSessionVersionMismatch,
)
from accessibility_toolkit.remote.messages import RemoteMessageType
from accessibility_toolkit.remote.transport.base import Transport


class RemoteSession:
    PROTOCOL_VERSION = 2

    def __init__(
        self,
        transport: Transport,
        on_event: Callable[[object], None],
    ) -> None:
        self.transport = transport
        self.on_event = on_event

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
        self.on_event(RemoteSessionDisconnected())

    def handle_message(self, payload: dict[str, Any]) -> bool:
        match payload.get("type"):
            case RemoteMessageType.CHANNEL_JOINED.value:
                self.on_event(RemoteSessionConnected())
                return True
            case RemoteMessageType.VERSION_MISMATCH.value:
                self.on_event(RemoteSessionVersionMismatch())
                return True
            case (
                RemoteMessageType.MOTD.value
                | RemoteMessageType.CLIENT_JOINED.value
                | RemoteMessageType.CLIENT_LEFT.value
                | RemoteMessageType.ERROR.value
            ):
                self.on_event(
                    RemotePeerMessageReceived(
                        message_type=str(payload.get("type", "")),
                        payload=payload,
                    )
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
