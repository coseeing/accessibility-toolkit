from enum import StrEnum

from interop.key import HID, KeyEvent


class KeyEchoHotkeyAction(StrEnum):
    START_ECHO = "start_echo"
    STOP_ECHO = "stop_echo"


class KeyEchoStateTransitionHotkeyUseCase:
    def __init__(self, *, mapping: dict[int, KeyEchoHotkeyAction]) -> None:
        self._mapping = dict(mapping)

    @classmethod
    def default(cls) -> "KeyEchoStateTransitionHotkeyUseCase":
        return cls(
            mapping={
                HID.ENTER: KeyEchoHotkeyAction.START_ECHO,
                HID.ESCAPE: KeyEchoHotkeyAction.STOP_ECHO,
            }
        )

    def match(self, event: KeyEvent) -> KeyEchoHotkeyAction | None:
        if not event.pressed:
            return None
        return self._mapping.get(event.usage)
