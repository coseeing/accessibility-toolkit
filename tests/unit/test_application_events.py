from application.events import (
    AppEvent,
    ClipboardAvailabilityChanged,
    ErrorRaised,
    HotkeyCaptureChanged,
    InputCaptureChanged,
    ModeChanged,
    SpeechEngineChanged,
    StatusEvent,
)


def test_shared_application_events_use_value_equality() -> None:
    assert ErrorRaised("boom") == ErrorRaised("boom")
    assert SpeechEngineChanged("default") == SpeechEngineChanged("default")
    assert InputCaptureChanged(True) == InputCaptureChanged(True)
    assert HotkeyCaptureChanged(False) == HotkeyCaptureChanged(False)
    assert ClipboardAvailabilityChanged(True) == ClipboardAvailabilityChanged(True)
    assert ModeChanged("echo", True) == ModeChanged("echo", True)


def test_app_event_list_accepts_shared_events() -> None:
    events: list[AppEvent] = [
        ErrorRaised("boom"),
        SpeechEngineChanged("default"),
        InputCaptureChanged(True),
        HotkeyCaptureChanged(False),
        ClipboardAvailabilityChanged(True),
        ModeChanged("echo", True),
    ]

    assert events == [
        ErrorRaised("boom"),
        SpeechEngineChanged("default"),
        InputCaptureChanged(True),
        HotkeyCaptureChanged(False),
        ClipboardAvailabilityChanged(True),
        ModeChanged("echo", True),
    ]


def test_status_event_from_payload_keeps_transitional_dict_support() -> None:
    payload = {
        "kind": "remote",
        "state": "connected",
        "type": "motd",
        "reason": "closed",
        "payload": {"message": "hi"},
    }

    assert StatusEvent.from_payload(payload) == StatusEvent(
        kind="remote",
        state="connected",
        type="motd",
        reason="closed",
        payload={"message": "hi"},
    )


def test_status_event_from_payload_coerces_optional_string_fields() -> None:
    event = StatusEvent.from_payload(
        {
            "kind": 123,
            "state": 456,
            "type": False,
            "reason": RuntimeError("closed"),
            "payload": {"ok": True},
        }
    )

    assert event == StatusEvent(
        kind="123",
        state="456",
        type="False",
        reason="closed",
        payload={"ok": True},
    )


def test_status_event_from_payload_drops_non_dict_payload() -> None:
    event = StatusEvent.from_payload(
        {
            "kind": "remote",
            "type": "motd",
            "payload": "not a dict",
        }
    )

    assert event == StatusEvent(kind="remote", type="motd", payload=None)
