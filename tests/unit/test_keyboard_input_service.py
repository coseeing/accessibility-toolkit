from accessibility_toolkit.input import KeyEventDecision
from accessibility_toolkit.input import CapturedKeyEvent
from accessibility_toolkit.input import KeyboardInputService
from accessibility_toolkit.input import HID, KeyEvent


class FakeCapture:
    def __init__(self):
        self.listener = None
        self.running = False

    def set_listener(self, listener):
        self.listener = listener

    def start(self):
        self.running = True

    def stop(self):
        self.running = False


class FakeHandler:
    def __init__(self):
        self.events = []

    def handle_key_event(self, event):
        self.events.append(event)
        return KeyEventDecision.PASS_THROUGH


def test_keyboard_input_service_forwards_events_to_handler():
    capture = FakeCapture()
    handler = FakeHandler()

    service = KeyboardInputService(capture, handler)
    service.bind()

    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)
    decision = capture.listener(CapturedKeyEvent(key_event=event, native_context=None))

    assert decision == KeyEventDecision.PASS_THROUGH
    assert handler.events == [CapturedKeyEvent(key_event=event, native_context=None)]


def test_keyboard_input_service_controls_capture_lifecycle():
    capture = FakeCapture()
    handler = FakeHandler()

    service = KeyboardInputService(capture, handler)

    service.start()
    assert capture.running is True

    service.stop()
    assert capture.running is False


def test_keyboard_input_service_binds_captured_key_event_listener():
    events = []

    class FakeCapture:
        def __init__(self):
            self.listener = None

        def set_listener(self, listener):
            self.listener = listener

        @property
        def running(self):
            return False

        def start(self):
            return None

        def stop(self):
            return None

    class FakeHandler:
        def handle_key_event(self, event):
            events.append(event)
            return "pass_through"

    capture = FakeCapture()
    service = KeyboardInputService(capture, FakeHandler())
    service.bind()

    captured = CapturedKeyEvent(
        key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True),
        native_context=None,
    )
    assert capture.listener(captured) == "pass_through"
    assert events == [captured]
