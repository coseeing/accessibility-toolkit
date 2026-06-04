from remote_core.models.speech_commands import (
    BreakCommand,
    IndexCommand,
    PitchCommand,
    RateCommand,
    SpeechCommand,
    VolumeCommand,
)
from remote_core.models.speech_sequence import SpeechSequence


def test_speech_sequence_restores_text_and_supported_commands():
    payload = {
        "sequence": [
            "hello",
            ["IndexCommand", {"index": 4}],
            ["BreakCommand", {"time": 75}],
            ["PitchCommand", {"offset": 12}],
            ["RateCommand", {"multiplier": 1.5}],
            ["VolumeCommand", {"multiplier": 0.5}],
            "world",
        ]
    }

    restored = SpeechSequence.from_remote_payload(payload)

    assert restored.items == (
        "hello",
        IndexCommand(index=4),
        BreakCommand(time=75),
        PitchCommand(offset=12),
        RateCommand(multiplier=1.5),
        VolumeCommand(multiplier=0.5),
        "world",
    )


def test_speech_sequence_preserves_unknown_command_as_generic_speech_command():
    payload = {"sequence": [["MyCommand", {"value": 3}]]}

    restored = SpeechSequence.from_remote_payload(payload)

    assert restored.items == (
        SpeechCommand(kind="MyCommand", data={"value": 3}),
    )


def test_speech_sequence_degrades_safely_for_malformed_supported_command_values():
    payload = {
        "sequence": [
            ["IndexCommand", {"index": "bad"}],
            ["BreakCommand", {"time": None}],
            ["PitchCommand", {"offset": object()}],
            ["RateCommand", {"multiplier": "fast"}],
            ["VolumeCommand", {"multiplier": []}],
        ]
    }

    restored = SpeechSequence.from_remote_payload(payload)

    assert restored.items == (
        IndexCommand(index=0),
        BreakCommand(time=0),
        PitchCommand(offset=0),
        RateCommand(multiplier=1.0),
        VolumeCommand(multiplier=1.0),
    )


def test_speech_sequence_preserves_already_restored_command_instances():
    payload = {
        "sequence": [
            "hello",
            BreakCommand(time=75),
            PitchCommand(offset=12),
        ]
    }

    restored = SpeechSequence.from_remote_payload(payload)

    assert restored.items == (
        "hello",
        BreakCommand(time=75),
        PitchCommand(offset=12),
    )
