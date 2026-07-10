from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KeyEvent:
    usage_page: int
    usage: int
    pressed: bool

    def to_local_payload(self) -> dict[str, int | bool]:
        return {
            "usage_page": self.usage_page,
            "usage": self.usage,
            "pressed": self.pressed,
        }


@dataclass(frozen=True)
class CapturedKeyEvent:
    key_event: KeyEvent
    native_context: object | None = None
    num_lock_on: bool | None = None
