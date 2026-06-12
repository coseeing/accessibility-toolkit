from interop.key.key_event import KeyEvent


class StateTransitionHotkeyPolicy:
    def __init__(self, *, mapping: dict[int, str]) -> None:
        self._mapping = dict(mapping)

    def match(self, event: KeyEvent) -> str | None:
        if not event.pressed:
            return None
        return self._mapping.get(event.vk)
