from collections.abc import Callable

from adapters.inputs.base import KeyEventDecision
from interop.key.key_event import KeyEvent


class NvdaRemoteInputForwardingUseCase:
    def __init__(
        self,
        *,
        is_connected: Callable[[], bool],
        is_controlling: Callable[[], bool],
        send_key: Callable[[dict[str, int | bool | None]], None],
        on_local_stop: Callable[[], None],
        local_stop_vk: int = 0x7A,
    ) -> None:
        self._is_connected = is_connected
        self._is_controlling = is_controlling
        self._send_key = send_key
        self._on_local_stop = on_local_stop
        self._local_stop_vk = local_stop_vk
        self._suppressed_keyups: set[int] = set()

    def handle(self, event: KeyEvent) -> KeyEventDecision:
        if not event.pressed and event.vk in self._suppressed_keyups:
            self._suppressed_keyups.discard(event.vk)
            return KeyEventDecision.SUPPRESS
        if not self._is_connected():
            return KeyEventDecision.PASS_THROUGH
        if event.vk == self._local_stop_vk and self._is_controlling():
            if event.pressed:
                self._on_local_stop()
                self._suppressed_keyups.add(event.vk)
            return KeyEventDecision.SUPPRESS
        if not self._is_controlling():
            return KeyEventDecision.PASS_THROUGH
        self._send_key(event.to_remote_payload())
        return KeyEventDecision.SUPPRESS

    def clear(self) -> None:
        self._suppressed_keyups.clear()
