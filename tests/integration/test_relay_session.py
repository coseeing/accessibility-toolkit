import socket
import ssl

import pytest

from interop.protocol.connection_info import ConnectionInfo
from interop.protocol.messages import RemoteMessageType
from interop.protocol.serializer import JSONSerializer
from interop.protocol.session.remote_session import RemoteSession
from interop.protocol.transport.relay import RelayTransport


def _recv_line(sock: socket.socket, buffer: bytearray) -> bytes:
    while b"\n" not in buffer:
        chunk = sock.recv(1024)
        if chunk == b"":
            raise ConnectionError("socket closed")
        buffer.extend(chunk)
    frame, _, remainder = bytes(buffer).partition(b"\n")
    buffer[:] = remainder
    return frame


def test_relay_transport_rejects_send_when_disconnected():
    transport = RelayTransport(serializer=JSONSerializer())

    with pytest.raises(RuntimeError, match="not connected"):
        transport.send(RemoteMessageType.PING)


def test_relay_session_connect_serializes_join_sequence():
    serializer = JSONSerializer()
    client, server = socket.socketpair()
    transport = RelayTransport(
        serializer=serializer,
        socket_factory=lambda _host, _port: client,
        use_tls=False,
    )
    status_events = []
    session = RemoteSession(transport=transport, on_event=status_events.append)

    session.connect(ConnectionInfo(hostname="example.com", port=6837, key="secret"))

    assert transport.connected is True
    assert transport.connected_to == ("example.com", 6837, False)
    recv_buffer = bytearray()
    decoded = [
        serializer.deserialize(_recv_line(server, recv_buffer)),
        serializer.deserialize(_recv_line(server, recv_buffer)),
    ]
    assert decoded == [
        {"version": 2, "type": "protocol_version"},
        {"channel": "secret", "mode": "master", "type": "join"},
    ]
    assert status_events == []
    transport.close()
    server.close()


def test_relay_transport_sends_and_receives_newline_json_with_partial_frames():
    serializer = JSONSerializer()
    client, server = socket.socketpair()
    transport = RelayTransport(
        serializer=serializer,
        socket_factory=lambda _host, _port: client,
        use_tls=False,
    )
    transport.connect("example.com", 6837)

    transport.send(RemoteMessageType.PING, sequence=1)
    assert serializer.deserialize(server.recv(1024).strip()) == {
        "type": "ping",
        "sequence": 1,
    }

    server.sendall(b'{"type":"mot')
    server.sendall(b'd","message":"hello"}\n{"type":"ping"}\n')

    assert transport.receive_once() == {"type": "motd", "message": "hello"}
    assert transport.receive_once() == {"type": "ping"}
    transport.close()
    server.close()


def test_relay_transport_logs_received_speak_frame(caplog):
    serializer = JSONSerializer()
    client, server = socket.socketpair()
    transport = RelayTransport(
        serializer=serializer,
        socket_factory=lambda _host, _port: client,
        use_tls=False,
    )
    transport.connect("example.com", 6837)

    server.sendall(
        b'{"type":"speak","sequence":["hello",["PitchCommand",{"offset":20}],"W"]}\n'
    )

    with caplog.at_level("DEBUG"):
        payload = transport.receive_once()

    assert payload["type"] == "speak"
    assert "Relay transport received frame" in caplog.text
    assert "PitchCommand" in caplog.text
    transport.close()
    server.close()


class FakeWrappedSocket:
    def __init__(self):
        self.sent = []

    def sendall(self, data):
        self.sent.append(data)

    def recv(self, _size):
        return b""

    def close(self):
        return None

    def shutdown(self, _how):
        return None


class FakeSSLContext:
    def __init__(self):
        self.check_hostname = True
        self.verify_mode = ssl.CERT_REQUIRED
        self.calls = []

    def wrap_socket(self, raw_socket, server_hostname):
        self.calls.append(
            (raw_socket, server_hostname, self.check_hostname, self.verify_mode)
        )
        return raw_socket


def test_relay_transport_insecure_connection_still_uses_tls_without_verification():
    serializer = JSONSerializer()
    fake_socket = FakeWrappedSocket()
    fake_context = FakeSSLContext()
    transport = RelayTransport(
        serializer=serializer,
        socket_factory=lambda _host, _port: fake_socket,
        ssl_context_factory=lambda: fake_context,
        use_tls=True,
    )

    transport.connect("example.com", 6837, insecure=True)

    assert transport.connected is True
    assert fake_context.calls == [
        (fake_socket, "example.com", False, ssl.CERT_NONE),
    ]
