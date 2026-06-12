import logging
from collections.abc import Callable

from adapters.inputs.base import KeyEventDecision
from apps.nvda_remote.legacy_key_payload import key_event_to_legacy_remote_payload
from interop.key.key_event import KeyEvent

_logger = logging.getLogger(__name__)


class NvdaRemoteInputForwardingUseCase:
    def __init__(
        self,
        *,
        is_connected: Callable[[], bool],
        is_controlling: Callable[[], bool],
        send_key: Callable[[dict[str, int | bool]], None],
        on_local_stop: Callable[[], None],
        local_stop_usage: int = 0x44,
    ) -> None:
        self._is_connected = is_connected
        self._is_controlling = is_controlling
        self._send_key = send_key
        self._on_local_stop = on_local_stop
        self._local_stop_usage = local_stop_usage
        self._suppressed_keyups: set[int] = set()

    def handle(self, event: KeyEvent) -> KeyEventDecision:
        if not event.pressed and event.usage in self._suppressed_keyups:
            self._suppressed_keyups.discard(event.usage)
            return KeyEventDecision.SUPPRESS
        if not self._is_connected():
            return KeyEventDecision.PASS_THROUGH
        if event.usage == self._local_stop_usage and self._is_controlling():
            if event.pressed:
                self._on_local_stop()
                self._suppressed_keyups.add(event.usage)
            return KeyEventDecision.SUPPRESS
        if not self._is_controlling():
            return KeyEventDecision.PASS_THROUGH
        try:
            self._send_key(key_event_to_legacy_remote_payload(event))
        except ValueError:
            _logger.debug(
                "Cannot forward HID 0x%02X:0x%02X — unsupported usage",
                event.usage_page,
                event.usage,
            )
            return KeyEventDecision.SUPPRESS
        return KeyEventDecision.SUPPRESS

    def clear(self) -> None:
        self._suppressed_keyups.clear()
