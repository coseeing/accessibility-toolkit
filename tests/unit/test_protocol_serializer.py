import pytest

from remote_core.connection_info import ConnectionInfo, ConnectionMode
from remote_core.models.keys import KeyEvent
from remote_core.models.speech_commands import BreakCommand, PitchCommand
from remote_core.protocol import RemoteMessageType, address_to_host_port
from remote_core.serializer import JSONSerializer


def test_serializer_imports_are_available():
    serializer = JSONSerializer()
    assert RemoteMessageType.KEY.value == "key"
    assert serializer.SEP == b"\n"


def test_protocol_helpers_and_serializer_round_trip():
    serializer = JSONSerializer()
    payload = serializer.serialize(
        RemoteMessageType.KEY,
        vk_code=9,
        scan_code=15,
        extended=False,
        pressed=True,
    )
    decoded = serializer.deserialize(payload.strip())
    assert address_to_host_port("example.com") == ("example.com", 6837)
    assert decoded["type"] == "key"
    assert decoded["vk_code"] == 9


def test_key_event_to_message_payload():
    event = KeyEvent(vk=65, scan=30, extended=False, pressed=True)
    assert event.to_remote_payload() == {
        "vk_code": 65,
        "scan_code": 30,
        "extended": False,
        "pressed": True,
    }


def test_connection_info_defaults_to_master_mode():
    connection_info = ConnectionInfo(hostname="example.com", port=6837, key="secret")
    assert connection_info.mode is ConnectionMode.MASTER
    assert connection_info.mode.value == "master"


def test_serializer_restores_speak_sequence_during_deserialize():
    serializer = JSONSerializer()
    payload = (
        b'{"type":"speak","sequence":["hello",["BreakCommand",{"time":40}],["PitchCommand",{"offset":2}]]}\n'
    )

    decoded = serializer.deserialize(payload.strip())

    assert decoded["sequence"] == [
        "hello",
        BreakCommand(time=40),
        PitchCommand(offset=2),
    ]


@pytest.mark.parametrize("payload", [b"[]", b'"text"', b"null"])
def test_serializer_deserialize_rejects_non_object_payloads(payload):
    serializer = JSONSerializer()
    with pytest.raises(ValueError, match="JSON object"):
        serializer.deserialize(payload)
