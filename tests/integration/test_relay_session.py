import socket

import pytest

from remote_core.connection_info import ConnectionInfo
from remote_core.protocol import RemoteMessageType
from remote_core.serializer import JSONSerializer
from remote_core.session.remote_session import RemoteSession
from remote_core.transport.relay import RelayTransport


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
    session = RemoteSession(transport=transport, on_status=status_events.append)

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
