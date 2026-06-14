from dataclasses import dataclass

from interop.key.key_event import KeyEvent


@dataclass(frozen=True)
class CapturedKeyEvent:
    key_event: KeyEvent
    native_context: object | None = None
