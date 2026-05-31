from remote_core.models.speech import NormalizedSpeech, SpeechSegment


def test_normalized_speech_from_remote_payload():
    payload = {
        "type": "speak",
        "sequence": ["Hello", ["BreakCommand", {"time": 100}], "world"],
    }
    normalized = NormalizedSpeech.from_remote_payload(payload)
    assert normalized.segments == [
        SpeechSegment(kind="text", value="Hello"),
        SpeechSegment(kind="break", value=100),
        SpeechSegment(kind="text", value="world"),
    ]
