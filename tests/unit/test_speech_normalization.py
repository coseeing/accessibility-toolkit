from remote_core.models.speech import NormalizedSpeech, SpeechSegment


def test_normalized_speech_from_remote_payload():
    payload = {
        "type": "speak",
        "sequence": ["Hello", ["BreakCommand", {"time": 100}], "world"],
    }
    normalized = NormalizedSpeech.from_remote_payload(payload)
    assert normalized.segments == (
        SpeechSegment(kind="text", value="Hello"),
        SpeechSegment(kind="break", value=100),
        SpeechSegment(kind="text", value="world"),
    )


def test_normalized_speech_ignores_unknown_and_malformed_commands():
    payload = {
        "type": "speak",
        "sequence": [
            "Hello",
            ["UnknownCommand", {"value": "ignored"}],
            ["BreakCommand"],
            ["BreakCommand", "not-a-dict"],
            ["BreakCommand", {"time": 50}],
        ],
    }
    normalized = NormalizedSpeech.from_remote_payload(payload)
    assert normalized.segments == (
        SpeechSegment(kind="text", value="Hello"),
        SpeechSegment(kind="break", value=50),
    )
