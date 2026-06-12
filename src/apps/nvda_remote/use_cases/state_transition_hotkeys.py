from enum import StrEnum

from interop.key import HID, KeyEvent


class NvdaRemoteHotkeyAction(StrEnum):
    TOGGLE_CONTROL = "toggle_control"


class NvdaRemoteStateTransitionHotkeyUseCase:
    def __init__(self, *, mapping: dict[int, NvdaRemoteHotkeyAction]) -> None:
        self._mapping = dict(mapping)

    @classmethod
    def default(cls) -> "NvdaRemoteStateTransitionHotkeyUseCase":
        return cls(mapping={HID.F11: NvdaRemoteHotkeyAction.TOGGLE_CONTROL})

    def match(self, event: KeyEvent) -> NvdaRemoteHotkeyAction | None:
        if not event.pressed:
            return None
        return self._mapping.get(event.usage)
