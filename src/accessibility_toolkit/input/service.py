from typing import Protocol

from accessibility_toolkit.input.capture import InputCapture
from accessibility_toolkit.input.events import CapturedKeyEvent
from accessibility_toolkit.input.results import KeyboardPipelineResult


class KeyEventHandler(Protocol):
    def handle_key_event(self, event: CapturedKeyEvent) -> KeyboardPipelineResult: ...


class KeyboardInputService:
    def __init__(self, capture: InputCapture, handler: KeyEventHandler) -> None:
        self._capture = capture
        self._handler = handler

    def bind(self) -> None:
        self._capture.set_listener(self._handler.handle_key_event)

    def set_handler(self, handler: KeyEventHandler) -> None:
        self._handler = handler
        self.bind()

    @property
    def running(self) -> bool:
        return self._capture.running

    def start(self) -> None:
        self.bind()
        self._capture.start()

    def stop(self) -> None:
        self._capture.stop()
