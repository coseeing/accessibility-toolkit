from accessibility_toolkit.interop.speech.speech_commands import (
    BreakCommand,
    IndexCommand,
    PitchCommand,
    RateCommand,
    SpeechCommand,
    VolumeCommand,
    restore_speech_command,
)
from accessibility_toolkit.interop.speech.speech_sequence import SpeechSequence


def test_speech_sequence_restores_text_and_supported_commands():
    payload = {
        "sequence": [
            "hello",
            ["IndexCommand", {"index": 4}],
            ["BreakCommand", {"time": 75}],
            ["PitchCommand", {"multiplier": 1.2}],
            ["PitchCommand", {"offset": 12}],
            ["RateCommand", {"offset": -15}],
            ["RateCommand", {"multiplier": 1.5}],
            ["VolumeCommand", {"offset": 8}],
            ["VolumeCommand", {"multiplier": 0.5}],
            "world",
        ]
    }

    restored = SpeechSequence.from_remote_payload(payload)

    assert restored.items == (
        "hello",
        IndexCommand(index=4),
        BreakCommand(time=75),
        PitchCommand(multiplier=1.2),
        PitchCommand(offset=12),
        RateCommand(offset=-15),
        RateCommand(multiplier=1.5),
        VolumeCommand(offset=8),
        VolumeCommand(multiplier=0.5),
        "world",
    )


def test_speech_sequence_logs_restored_sequence(caplog):
    payload = {
        "sequence": [
            "hello",
            ["PitchCommand", {"offset": 12}],
            "world",
        ]
    }

    with caplog.at_level("DEBUG"):
        restored = SpeechSequence.from_remote_payload(payload)

    assert restored.items == ("hello", PitchCommand(offset=12), "world")
    assert "SpeechSequence.from_remote_payload restored" in caplog.text


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
            ["PitchCommand", {"multiplier": object()}],
            ["RateCommand", {"offset": "fast"}],
            ["RateCommand", {"multiplier": "fast"}],
            ["VolumeCommand", {"offset": []}],
            ["VolumeCommand", {"multiplier": []}],
        ]
    }

    restored = SpeechSequence.from_remote_payload(payload)

    assert restored.items == (
        IndexCommand(index=0),
        BreakCommand(time=0),
        PitchCommand(),
        PitchCommand(),
        RateCommand(),
        RateCommand(),
        VolumeCommand(),
        VolumeCommand(),
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


def test_speech_sequence_rejects_invalid_local_prosody_payloads():
    payload = {
        "sequence": [
            "hello",
            ["PitchCommand", {"offset": 1, "multiplier": 1.1}],
            "world",
        ]
    }

    try:
        SpeechSequence.from_remote_payload(payload)
    except ValueError as error:
        assert str(error) == "offset and multiplier cannot both be non-default"
    else:
        assert False, "SpeechSequence accepted an invalid prosody payload"


def test_local_prosody_commands_report_mode_for_default_offset_and_multiplier():
    assert PitchCommand().mode == "default"
    assert PitchCommand(offset=12).mode == "offset"
    assert PitchCommand(multiplier=1.2).mode == "multiplier"

    assert RateCommand().mode == "default"
    assert RateCommand(offset=-10).mode == "offset"
    assert RateCommand(multiplier=1.5).mode == "multiplier"

    assert VolumeCommand().mode == "default"
    assert VolumeCommand(offset=8).mode == "offset"
    assert VolumeCommand(multiplier=0.75).mode == "multiplier"


def test_local_prosody_commands_reject_non_default_offset_and_multiplier_together():
    invalid_cases = (
        (PitchCommand, {"offset": 3, "multiplier": 1.1}),
        (RateCommand, {"offset": -5, "multiplier": 0.9}),
        (VolumeCommand, {"offset": 7, "multiplier": 1.2}),
    )

    for command_type, kwargs in invalid_cases:
        try:
            command_type(**kwargs)
        except ValueError as error:
            assert str(error) == "offset and multiplier cannot both be non-default"
        else:
            assert False, f"{command_type.__name__} accepted invalid args: {kwargs}"


def test_restore_speech_command_restores_local_prosody_offset_and_multiplier_modes():
    assert restore_speech_command("PitchCommand", {"offset": 12}) == PitchCommand(offset=12)
    assert restore_speech_command("PitchCommand", {"multiplier": 1.3}) == PitchCommand(
        multiplier=1.3
    )
    assert restore_speech_command("RateCommand", {"offset": -5}) == RateCommand(offset=-5)
    assert restore_speech_command("RateCommand", {"multiplier": 1.5}) == RateCommand(
        multiplier=1.5
    )
    assert restore_speech_command("VolumeCommand", {"offset": 9}) == VolumeCommand(offset=9)
    assert restore_speech_command("VolumeCommand", {"multiplier": 0.5}) == VolumeCommand(
        multiplier=0.5
    )


def test_restore_speech_command_supports_nvda_internal_prosody_fields():
    assert restore_speech_command(
        "PitchCommand",
        {"_offset": 30, "_multiplier": 1, "isDefault": False},
    ) == PitchCommand(offset=30)
    assert restore_speech_command(
        "RateCommand",
        {"_offset": -5, "_multiplier": 1, "isDefault": False},
    ) == RateCommand(offset=-5)
    assert restore_speech_command(
        "VolumeCommand",
        {"_offset": 0, "_multiplier": 0.8, "isDefault": False},
    ) == VolumeCommand(multiplier=0.8)


def test_restore_speech_command_rejects_invalid_local_prosody_payloads():
    invalid_cases = (
        ("PitchCommand", {"offset": 1, "multiplier": 1.1}),
        ("RateCommand", {"offset": -2, "multiplier": 0.9}),
        ("VolumeCommand", {"offset": 4, "multiplier": 1.2}),
    )

    for kind, data in invalid_cases:
        try:
            restore_speech_command(kind, data)
        except ValueError as error:
            assert str(error) == "offset and multiplier cannot both be non-default"
        else:
            assert False, f"{kind} accepted invalid payload: {data}"
