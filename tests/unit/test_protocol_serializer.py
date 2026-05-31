from remote_core.models.keys import KeyEvent
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
        vk=9,
        scan=15,
        extended=False,
        pressed=True,
    )
    decoded = serializer.deserialize(payload.strip())
    assert address_to_host_port("example.com") == ("example.com", 6837)
    assert decoded["type"] == "key"
    assert decoded["vk"] == 9


def test_key_event_to_message_payload():
    event = KeyEvent(vk=65, scan=30, extended=False, pressed=True)
    assert event.to_remote_payload() == {
        "vk": 65,
        "scan": 30,
        "extended": False,
        "pressed": True,
    }
