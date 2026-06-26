from interop.protocol.events import (
    RemotePeerMessageReceived,
    RemoteSessionConnected,
    RemoteSessionDisconnected,
    RemoteSessionVersionMismatch,
)
from interop.protocol.session.remote_session import RemoteSession


class DummyTransport:
    def __init__(self) -> None:
        self.closed = False
        self.sent = []

    def connect(self, host, port, insecure=False):
        self.sent.append(("connect", host, port, insecure))

    def send(self, message_type, **payload):
        self.sent.append((message_type, payload))

    def close(self):
        self.closed = True


def test_session_reports_connected_after_channel_joined():
    seen = []
    session = RemoteSession(transport=DummyTransport(), on_event=seen.append)

    assert session.handle_message({"type": "channel_joined"}) is True

    assert seen == [RemoteSessionConnected()]


def test_session_disconnect_emits_disconnected_event():
    seen = []
    transport = DummyTransport()
    session = RemoteSession(transport=transport, on_event=seen.append)

    session.disconnect()

    assert transport.closed is True
    assert seen == [RemoteSessionDisconnected()]


def test_session_emits_version_mismatch_and_remote_messages():
    seen = []
    session = RemoteSession(transport=DummyTransport(), on_event=seen.append)
    motd = {"type": "motd", "message": "hello"}

    assert session.handle_message({"type": "version_mismatch"}) is True
    assert session.handle_message(motd) is True

    assert seen == [
        RemoteSessionVersionMismatch(),
        RemotePeerMessageReceived(message_type="motd", payload=motd),
    ]
