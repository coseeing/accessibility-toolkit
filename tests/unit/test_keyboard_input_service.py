from adapters.inputs.base import KeyEventDecision
from application.keyboard import KeyboardInputService
from interop.key import HID, KeyEvent


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
    decision = capture.listener(event)

    assert decision == KeyEventDecision.PASS_THROUGH
    assert handler.events == [event]


def test_keyboard_input_service_controls_capture_lifecycle():
    capture = FakeCapture()
    handler = FakeHandler()

    service = KeyboardInputService(capture, handler)

    service.start()
    assert capture.running is True

    service.stop()
    assert capture.running is False
