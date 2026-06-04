from remote_core.models.speech_commands import (
    BreakCommand,
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
