import pytest

from remote_core.connection_info import ConnectionInfo
from remote_core.protocol import RemoteMessageType
from remote_core.serializer import JSONSerializer
from remote_core.session.remote_session import RemoteSession
from remote_core.transport.relay import RelayTransport


def test_relay_transport_rejects_send_when_disconnected():
    transport = RelayTransport(serializer=JSONSerializer())

    with pytest.raises(RuntimeError, match="not connected"):
        transport.send(RemoteMessageType.PING)


def test_relay_session_connect_serializes_join_sequence():
    serializer = JSONSerializer()
    transport = RelayTransport(serializer=serializer)
    session = RemoteSession(transport=transport, on_status=lambda event: None)

    session.connect(ConnectionInfo(hostname="example.com", port=6837, key="secret"))

    assert transport.connected_to == ("example.com", 6837, False)
    decoded = [serializer.deserialize(message.strip()) for message in transport.sent]
    assert decoded == [
        {"version": 2, "type": "protocol_version"},
        {"channel": "secret", "mode": "master", "type": "join"},
    ]
