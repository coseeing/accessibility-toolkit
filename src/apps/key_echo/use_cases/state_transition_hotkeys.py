from enum import StrEnum

from interop.key.key_event import KeyEvent


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
                0x0D: KeyEchoHotkeyAction.START_ECHO,
                0x1B: KeyEchoHotkeyAction.STOP_ECHO,
            }
        )

    def match(self, event: KeyEvent) -> KeyEchoHotkeyAction | None:
        if not event.pressed:
            return None
        return self._mapping.get(event.vk)
