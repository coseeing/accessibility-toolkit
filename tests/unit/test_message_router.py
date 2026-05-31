from remote_core.connection_info import ConnectionInfo
from remote_core.models.speech import NormalizedSpeech, SpeechSegment
from remote_core.protocol import RemoteMessageType
from remote_core.routing.message_router import MessageRouter
from remote_core.session.remote_session import RemoteSession


class DummyTransport:
    def __init__(self):
        self.sent = []
        self.connected_to = None
        self.closed = False

    def connect(self, hostname, port, insecure=False):
        self.connected_to = (hostname, port, insecure)

    def send(self, message_type, **payload):
        self.sent.append((message_type, payload))

    def close(self):
        self.closed = True


def test_router_dispatches_speech_and_clipboard():
    seen = []
    router = MessageRouter(
        on_speech=lambda speech: seen.append(("speech", speech)),
        on_clipboard=lambda text: seen.append(("clipboard", text)),
        on_status=lambda event: seen.append(("status", event)),
    )

    router.handle_message({"type": "speak", "sequence": ["hello"]})
    router.handle_message({"type": "set_clipboard_text", "text": "abc"})

    assert seen[0] == (
        "speech",
        NormalizedSpeech(segments=(SpeechSegment(kind="text", value="hello"),)),
    )
    assert seen[1] == ("clipboard", "abc")


def test_router_dispatches_unknown_messages_to_status():
    seen = []
    router = MessageRouter(
        on_speech=lambda speech: seen.append(("speech", speech)),
        on_clipboard=lambda text: seen.append(("clipboard", text)),
        on_status=lambda event: seen.append(("status", event)),
    )
    payload = {"type": "motd", "message": "hello"}

    router.handle_message(payload)

    assert seen == [
        (
            "status",
            {"kind": "remote", "type": "motd", "payload": payload},
        )
    ]


def test_router_reports_missing_clipboard_text_as_invalid_message():
    seen = []
    router = MessageRouter(
        on_speech=lambda speech: seen.append(("speech", speech)),
        on_clipboard=lambda text: seen.append(("clipboard", text)),
        on_status=lambda event: seen.append(("status", event)),
    )
    payload = {"type": "set_clipboard_text"}

    router.handle_message(payload)

    assert seen == [
        (
            "status",
            {
                "kind": "invalid_message",
                "reason": "clipboard_text_must_be_string",
                "payload": payload,
            },
        )
    ]


def test_router_reports_none_clipboard_text_as_invalid_message():
    seen = []
    router = MessageRouter(
        on_speech=lambda speech: seen.append(("speech", speech)),
        on_clipboard=lambda text: seen.append(("clipboard", text)),
        on_status=lambda event: seen.append(("status", event)),
    )
    payload = {"type": "set_clipboard_text", "text": None}

    router.handle_message(payload)

    assert seen == [
        (
            "status",
            {
                "kind": "invalid_message",
                "reason": "clipboard_text_must_be_string",
                "payload": payload,
            },
        )
    ]


def test_router_reports_non_string_clipboard_text_as_invalid_message():
    seen = []
    router = MessageRouter(
        on_speech=lambda speech: seen.append(("speech", speech)),
        on_clipboard=lambda text: seen.append(("clipboard", text)),
        on_status=lambda event: seen.append(("status", event)),
    )
    payload = {"type": "set_clipboard_text", "text": 123}

    router.handle_message(payload)

    assert seen == [
        (
            "status",
            {
                "kind": "invalid_message",
                "reason": "clipboard_text_must_be_string",
                "payload": payload,
            },
        )
    ]


def test_session_join_sends_protocol_and_join_messages():
    transport = DummyTransport()
    status_events = []
    session = RemoteSession(
        transport=transport,
        on_status=status_events.append,
    )

    session.connect(ConnectionInfo(hostname="example.com", port=6837, key="secret"))

    assert transport.connected_to == ("example.com", 6837, False)
    assert transport.sent[0] == (RemoteMessageType.PROTOCOL_VERSION, {"version": 2})
    assert transport.sent[1][0] == RemoteMessageType.JOIN
    assert transport.sent[1][1] == {"channel": "secret", "mode": "master"}
    assert status_events == []


def test_session_reports_connected_after_channel_joined():
    transport = DummyTransport()
    status_events = []
    session = RemoteSession(
        transport=transport,
        on_status=status_events.append,
    )

    assert session.handle_message({"type": "channel_joined"}) is True

    assert status_events == [{"kind": "connection", "state": "connected"}]


def test_session_reports_connection_and_remote_status_messages():
    transport = DummyTransport()
    status_events = []
    session = RemoteSession(
        transport=transport,
        on_status=status_events.append,
    )
    motd = {"type": "motd", "message": "hello"}
    client_joined = {"type": "client_joined", "id": "abc"}
    client_left = {"type": "client_left", "id": "abc"}
    error = {"type": "error", "message": "bad"}

    assert session.handle_message({"type": "version_mismatch"}) is True
    assert session.handle_message(motd) is True
    assert session.handle_message(client_joined) is True
    assert session.handle_message(client_left) is True
    assert session.handle_message(error) is True
    assert session.handle_message({"type": "ping"}) is True

    assert status_events == [
        {"kind": "connection", "state": "version_mismatch"},
        {"kind": "remote", "type": "motd", "payload": motd},
        {"kind": "remote", "type": "client_joined", "payload": client_joined},
        {"kind": "remote", "type": "client_left", "payload": client_left},
        {"kind": "remote", "type": "error", "payload": error},
    ]


def test_session_does_not_handle_output_messages():
    transport = DummyTransport()
    status_events = []
    session = RemoteSession(
        transport=transport,
        on_status=status_events.append,
    )

    assert session.handle_message({"type": "speak", "sequence": ["hello"]}) is False

    assert status_events == []


def test_session_disconnect_closes_transport_and_sets_idle_status():
    transport = DummyTransport()
    status_events = []
    session = RemoteSession(
        transport=transport,
        on_status=status_events.append,
    )

    session.disconnect()

    assert transport.closed is True
    assert status_events == [{"kind": "connection", "state": "idle"}]
