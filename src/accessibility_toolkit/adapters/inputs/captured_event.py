from dataclasses import dataclass

from accessibility_toolkit.interop.key.key_event import KeyEvent


@dataclass(frozen=True)
class CapturedKeyEvent:
    key_event: KeyEvent
    native_context: object | None = None
    num_lock_on: bool | None = None
