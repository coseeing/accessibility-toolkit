from typing import Protocol

from adapters.inputs.base import InputCapture, KeyEventDecision
from remote_core.models.keys import KeyEvent


class KeyEventHandler(Protocol):
    def handle_key_event(self, event: KeyEvent) -> KeyEventDecision: ...


class KeyboardInputService:
    def __init__(self, capture: InputCapture, handler: KeyEventHandler) -> None:
        self._capture = capture
        self._handler = handler

    def bind(self) -> None:
        self._capture.set_listener(self._handler.handle_key_event)

    def set_handler(self, handler: KeyEventHandler) -> None:
        self._handler = handler
        self.bind()

    def start(self) -> None:
        self.bind()
        self._capture.start()

    def stop(self) -> None:
        self._capture.stop()
