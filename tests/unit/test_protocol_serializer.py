import pytest

from accessibility_toolkit.input import HID, KeyEvent
from accessibility_toolkit.output.speech import (
    BreakCommand,
    PitchCommand,
    RateCommand,
    SpeechCommand,
    SpeechSequence,
    VolumeCommand,
)
from accessibility_toolkit.interop.protocol.messages import RemoteMessageType, address_to_host_port
from accessibility_toolkit.interop.protocol.serializer import JSONSerializer


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
    from apps.nvda_remote.legacy_key_payload import key_event_to_legacy_remote_payload
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 65,
        "scan_code": 30,
        "extended": False,
        "pressed": True,
    }


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


@pytest.mark.parametrize(
    ("payload", "expected_sequence"),
    [
        (
            b'{"type":"speak","sequence":[["PitchCommand",{"offset":2}],["RateCommand",{"offset":-5}],["VolumeCommand",{"offset":9}]]}\n',
            [
                PitchCommand(offset=2),
                RateCommand(offset=-5),
                VolumeCommand(offset=9),
            ],
        ),
        (
            b'{"type":"speak","sequence":[["PitchCommand",{"multiplier":1.3}],["RateCommand",{"multiplier":1.5}],["VolumeCommand",{"multiplier":0.5}]]}\n',
            [
                PitchCommand(multiplier=1.3),
                RateCommand(multiplier=1.5),
                VolumeCommand(multiplier=0.5),
            ],
        ),
    ],
)
def test_serializer_deserialize_restores_prosody_payload_variants(
    payload, expected_sequence
):
    serializer = JSONSerializer()

    decoded = serializer.deserialize(payload.strip())

    assert decoded["sequence"] == expected_sequence
    assert SpeechSequence.from_remote_payload(decoded) == SpeechSequence(
        items=tuple(expected_sequence)
    )


def test_serializer_restores_nvda_internal_prosody_fields():
    serializer = JSONSerializer()
    payload = (
        b'{"type":"speak","sequence":[["PitchCommand",{"_offset":30,"_multiplier":1,"isDefault":false}],["RateCommand",{"_offset":-5,"_multiplier":1,"isDefault":false}],["VolumeCommand",{"_offset":0,"_multiplier":0.8,"isDefault":false}]]}\n'
    )

    decoded = serializer.deserialize(payload.strip())

    assert decoded["sequence"] == [
        PitchCommand(offset=30),
        RateCommand(offset=-5),
        VolumeCommand(multiplier=0.8),
    ]


def test_serializer_deserialize_preserves_unrecognized_sequence_items():
    serializer = JSONSerializer()
    payload = (
        b'{"type":"speak","sequence":["hello",{"text":"raw"},["UnknownCommand",{"value":1}],17,["PitchCommand",{"offset":2}]]}\n'
    )

    decoded = serializer.deserialize(payload.strip())

    assert decoded["sequence"] == [
        "hello",
        {"text": "raw"},
        SpeechCommand(kind="UnknownCommand", data={"value": 1}),
        17,
        PitchCommand(offset=2),
    ]
    assert SpeechSequence.from_remote_payload(decoded) == SpeechSequence(
        items=(
            "hello",
            SpeechCommand(kind="UnknownCommand", data={"value": 1}),
            PitchCommand(offset=2),
        )
    )


@pytest.mark.parametrize("payload", [b"[]", b'"text"', b"null"])
def test_serializer_deserialize_rejects_non_object_payloads(payload):
    serializer = JSONSerializer()
    with pytest.raises(ValueError, match="JSON object"):
        serializer.deserialize(payload)


def test_serializer_logs_raw_and_decoded_speak_payload(caplog):
    serializer = JSONSerializer()
    payload = (
        b'{"type":"speak","sequence":["hello",["PitchCommand",{"offset":20}],"W"]}\n'
    )

    with caplog.at_level("DEBUG"):
        decoded = serializer.deserialize(payload.strip())

    assert decoded["type"] == "speak"
    assert "JSONSerializer.deserialize input" in caplog.text
    assert "JSONSerializer.deserialize output type='speak'" in caplog.text


def test_key_event_to_local_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)
    assert event.to_local_payload() == {
        "usage_page": 0x07,
        "usage": 0x04,
        "pressed": True,
    }
