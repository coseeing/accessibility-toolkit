from interop.speech.speech_commands import BreakCommand
from interop.speech.speech_sequence import SpeechSequence
from interop.protocol.messages import RemoteMessageType
from interop.protocol.routing.message_router import MessageRouter
from interop.protocol.events import (
    RemotePeerMessageReceived,
    RemoteProtocolMessageInvalid,
)
from application.output import Manager


class DummyTransport:
    def __init__(self):
        self.sent = []
        self.connected_to = None
        self.closed = False

    def connect(self, hostname, port, insecure=False):
        self.connected_to = (hostname, port, insecure)

    def send(self, message_type, **payload):
        self.sent.append((message_type, payload))

    def close(self):
        self.closed = True


class FakeClipboard:
    def __init__(self):
        self.text = ""

    def set_text(self, text: str) -> None:
        self.text = text

    def get_text(self) -> str:
        return self.text


def build_router(seen):
    return MessageRouter(
        on_speech=lambda speech: seen.append(("speech", speech)),
        on_cancel=lambda: seen.append(("cancel", None)),
        on_pause=lambda paused: seen.append(("pause", paused)),
        on_clipboard=lambda text: seen.append(("clipboard", text)),
        on_tone=lambda hz, length, left, right: seen.append(
            ("tone", hz, length, left, right)
        ),
        on_status=lambda event: seen.append(("status", event)),
    )


def test_router_dispatches_speech_and_clipboard():
    seen = []
    router = build_router(seen)

    router.handle_message(
        {
            "type": "speak",
            "sequence": ["hello", ["BreakCommand", {"time": 50}], "world"],
        }
    )
    router.handle_message({"type": "set_clipboard_text", "text": "abc"})

    assert seen[0] == (
        "speech",
        SpeechSequence(items=("hello", BreakCommand(time=50), "world")),
    )
    assert seen[1] == ("clipboard", "abc")


def test_sequence_routes_from_router_to_backend_through_output_manager():
    seen = []

    class FakeBackend:
        def speak(self, sequence):
            seen.append(sequence)

        def cancel(self):
            return None

        def pause(self, is_paused):
            return None

        def list_voices(self):
            return ()

        def get_voice(self):
            return None

        def set_voice(self, voice_id):
            return None

        def get_rate(self):
            return None

        def set_rate(self, value):
            return None

        def get_pitch(self):
            return None

        def set_pitch(self, value):
            return None

        def get_volume(self):
            return None

        def set_volume(self, value):
            return None

    router = MessageRouter(
        on_speech=lambda sequence: Manager(
            FakeBackend(), FakeClipboard()
        ).handle_speech(sequence),
        on_cancel=lambda: None,
        on_pause=lambda paused: None,
        on_clipboard=lambda text: None,
        on_tone=lambda hz, length, left, right: None,
        on_status=lambda event: None,
    )

    router.handle_message(
        {
            "type": "speak",
            "sequence": ["hello", ["BreakCommand", {"time": 10}], "world"],
        }
    )

    assert seen == [
        SpeechSequence(items=("hello", BreakCommand(time=10), "world"))
    ]


def test_router_preserves_already_restored_speech_commands():
    seen = []
    router = build_router(seen)

    router.handle_message(
        {
            "type": "speak",
            "sequence": ["hello", BreakCommand(time=50), "world"],
        }
    )

    assert seen == [
        (
            "speech",
            SpeechSequence(items=("hello", BreakCommand(time=50), "world")),
        )
    ]


def test_router_dispatches_unknown_messages_to_status():
    seen = []
    router = build_router(seen)
    payload = {"type": "motd", "message": "hello"}

    router.handle_message(payload)

    assert seen == [
        (
            "status",
            RemotePeerMessageReceived(message_type="motd", payload=payload),
        )
    ]


def test_router_reports_missing_clipboard_text_as_invalid_message():
    seen = []
    router = build_router(seen)
    payload = {"type": "set_clipboard_text"}

    router.handle_message(payload)

    assert seen == [
        (
            "status",
            RemoteProtocolMessageInvalid(
                reason="clipboard_text_must_be_string",
                payload=payload,
            ),
        )
    ]


def test_router_reports_none_clipboard_text_as_invalid_message():
    seen = []
    router = build_router(seen)
    payload = {"type": "set_clipboard_text", "text": None}

    router.handle_message(payload)

    assert seen == [
        (
            "status",
            RemoteProtocolMessageInvalid(
                reason="clipboard_text_must_be_string",
                payload=payload,
            ),
        )
    ]


def test_router_reports_non_string_clipboard_text_as_invalid_message():
    seen = []
    router = build_router(seen)
    payload = {"type": "set_clipboard_text", "text": 123}

    router.handle_message(payload)

    assert seen == [
        (
            "status",
            RemoteProtocolMessageInvalid(
                reason="clipboard_text_must_be_string",
                payload=payload,
            ),
        )
    ]


def test_router_dispatches_cancel_and_pause_messages():
    seen = []
    router = build_router(seen)

    router.handle_message({"type": "cancel"})
    router.handle_message({"type": "pause_speech", "switch": True})

    assert seen == [
        ("cancel", None),
        ("pause", True),
    ]


def test_router_reports_invalid_pause_payload():
    seen = []
    router = build_router(seen)
    payload = {"type": "pause_speech", "switch": "yes"}

    router.handle_message(payload)

    assert seen == [
        (
            "status",
            RemoteProtocolMessageInvalid(
                reason="pause_switch_must_be_bool",
                payload=payload,
            ),
        )
    ]


def test_router_reports_infinity_tone_length_as_invalid_message() -> None:
    seen = []
    router = build_router(seen)
    payload = {
        "type": "tone",
        "hz": 440,
        "length": float("inf"),
        "left": 50,
        "right": 50,
    }

    router.handle_message(payload)

    assert seen == [
        (
            "status",
            RemoteProtocolMessageInvalid(
                reason="tone_fields_must_be_numeric",
                payload=payload,
            ),
        )
    ]


def test_router_reports_infinity_tone_left_as_invalid_message() -> None:
    seen = []
    router = build_router(seen)
    payload = {
        "type": "tone",
        "hz": 440,
        "length": 80,
        "left": float("inf"),
        "right": 50,
    }

    router.handle_message(payload)

    assert seen == [
        (
            "status",
            RemoteProtocolMessageInvalid(
                reason="tone_fields_must_be_numeric",
                payload=payload,
            ),
        )
    ]


def test_router_reports_infinity_tone_right_as_invalid_message() -> None:
    seen = []
    router = build_router(seen)
    payload = {
        "type": "tone",
        "hz": 440,
        "length": 80,
        "left": 50,
        "right": float("inf"),
    }

    router.handle_message(payload)

    assert seen == [
        (
            "status",
            RemoteProtocolMessageInvalid(
                reason="tone_fields_must_be_numeric",
                payload=payload,
            ),
        )
    ]


def test_remote_message_type_includes_nvda_remote_tone_value() -> None:
    assert RemoteMessageType.TONE.value == "tone"


def test_router_dispatches_tone_message() -> None:
    seen = []
    router = build_router(seen)

    router.handle_message(
        {
            "type": "tone",
            "hz": 440,
            "length": 80,
            "left": 25,
            "right": 75,
        }
    )

    assert seen == [("tone", 440.0, 80, 25, 75)]


def test_router_clamps_tone_balance_and_non_negative_duration() -> None:
    seen = []
    router = build_router(seen)

    router.handle_message(
        {
            "type": "tone",
            "hz": -10,
            "length": -5,
            "left": -20,
            "right": 250,
        }
    )

    assert seen == [("tone", 0.0, 0, 0, 100)]


def test_router_reports_missing_tone_field_as_invalid_message() -> None:
    seen = []
    router = build_router(seen)
    payload = {"type": "tone", "hz": 440, "length": 80, "left": 50}

    router.handle_message(payload)

    assert seen == [
        (
            "status",
            RemoteProtocolMessageInvalid(
                reason="tone_fields_must_be_numeric",
                payload=payload,
            ),
        )
    ]


def test_router_reports_non_numeric_tone_field_as_invalid_message() -> None:
    seen = []
    router = build_router(seen)
    payload = {
        "type": "tone",
        "hz": "high",
        "length": 80,
        "left": 50,
        "right": 50,
    }

    router.handle_message(payload)

    assert seen == [
        (
            "status",
            RemoteProtocolMessageInvalid(
                reason="tone_fields_must_be_numeric",
                payload=payload,
            ),
        )
    ]


def test_router_clamps_tone_hz_and_length_to_maximum_bounds() -> None:
    seen = []
    router = build_router(seen)

    router.handle_message(
        {
            "type": "tone",
            "hz": 50000,
            "length": 30000,
            "left": 50,
            "right": 50,
        }
    )

    assert seen == [("tone", 20000.0, 5000, 50, 50)]


def test_router_reports_infinity_tone_hz_as_invalid_message() -> None:
    seen = []
    router = build_router(seen)
    payload = {
        "type": "tone",
        "hz": float("inf"),
        "length": 80,
        "left": 50,
        "right": 50,
    }

    router.handle_message(payload)

    assert seen == [
        (
            "status",
            RemoteProtocolMessageInvalid(
                reason="tone_fields_must_be_numeric",
                payload=payload,
            ),
        )
    ]


def test_router_reports_nan_tone_hz_as_invalid_message() -> None:
    seen = []
    router = build_router(seen)
    payload = {
        "type": "tone",
        "hz": float("nan"),
        "length": 80,
        "left": 50,
        "right": 50,
    }

    router.handle_message(payload)

    assert seen == [
        (
            "status",
            RemoteProtocolMessageInvalid(
                reason="tone_fields_must_be_numeric",
                payload=payload,
            ),
        )
    ]
