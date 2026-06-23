from application.events import (
    AppEvent,
    ClipboardAvailabilityChanged,
    ErrorRaised,
    HotkeyCaptureChanged,
    InputCaptureChanged,
    ModeChanged,
    SpeechBackendChanged,
    StatusEvent,
)


def test_shared_application_events_use_value_equality() -> None:
    assert ErrorRaised("boom") == ErrorRaised("boom")
    assert SpeechBackendChanged("default") == SpeechBackendChanged("default")
    assert InputCaptureChanged(True) == InputCaptureChanged(True)
    assert HotkeyCaptureChanged(False) == HotkeyCaptureChanged(False)
    assert ClipboardAvailabilityChanged(True) == ClipboardAvailabilityChanged(True)
    assert ModeChanged("echo", True) == ModeChanged("echo", True)


def test_app_event_list_accepts_shared_events() -> None:
    events: list[AppEvent] = [
        ErrorRaised("boom"),
        SpeechBackendChanged("default"),
        InputCaptureChanged(True),
        HotkeyCaptureChanged(False),
        ClipboardAvailabilityChanged(True),
        ModeChanged("echo", True),
    ]

    assert events == [
        ErrorRaised("boom"),
        SpeechBackendChanged("default"),
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
