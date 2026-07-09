from accessibility_toolkit.application.events import (
    AppEvent,
    ClipboardAvailabilityChanged,
    ErrorRaised,
    HotkeyCaptureChanged,
    InputCaptureChanged,
    ModeChanged,
    SpeechEngineChanged,
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
