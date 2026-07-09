from apps.nvda_remote.events import RemoteConnectionChanged, RemoteMessageReceived
from accessibility_toolkit.interop.protocol.events import (
    RemotePeerMessageReceived,
    RemoteSessionConnected,
    RemoteSessionDisconnected,
    RemoteSessionVersionMismatch,
)


class RemoteProtocolEventHandler:
    def __init__(self, *, on_connected, on_disconnected, notify_remote_message) -> None:
        self._on_connected = on_connected
        self._on_disconnected = on_disconnected
        self._notify_remote_message = notify_remote_message

    def handle(self, event: object) -> None:
        match event:
            case RemoteSessionConnected():
                self._on_connected()
            case RemoteSessionDisconnected():
                self._on_disconnected()
            case RemoteSessionVersionMismatch():
                self._notify_remote_message(RemoteConnectionChanged("version_mismatch"))
            case RemotePeerMessageReceived(message_type=message_type, payload=payload):
                self._notify_remote_message(RemoteMessageReceived(message_type, payload))
