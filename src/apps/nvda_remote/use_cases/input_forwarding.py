import logging
from collections.abc import Callable

from adapters.inputs.base import KeyEventDecision
from adapters.inputs.captured_event import CapturedKeyEvent
from apps.nvda_remote.legacy_key_payload_bridge import legacy_payload_from_captured_event

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
        use_windows_native_key_payload: bool = False,
    ) -> None:
        self._is_connected = is_connected
        self._is_controlling = is_controlling
        self._send_key = send_key
        self._on_local_stop = on_local_stop
        self._local_stop_usage = local_stop_usage
        self._use_windows_native_key_payload = use_windows_native_key_payload
        self._suppressed_keyups: set[int] = set()

    def handle(self, event: CapturedKeyEvent) -> KeyEventDecision:
        key_event = event.key_event
        if not key_event.pressed and key_event.usage in self._suppressed_keyups:
            self._suppressed_keyups.discard(key_event.usage)
            return KeyEventDecision.SUPPRESS
        if not self._is_connected():
            return KeyEventDecision.PASS_THROUGH
        if key_event.usage == self._local_stop_usage and self._is_controlling():
            if key_event.pressed:
                self._on_local_stop()
                self._suppressed_keyups.add(key_event.usage)
            return KeyEventDecision.SUPPRESS
        if not self._is_controlling():
            return KeyEventDecision.PASS_THROUGH
        try:
            self._send_key(
                legacy_payload_from_captured_event(
                    event,
                    use_windows_native_key_payload=self._use_windows_native_key_payload,
                )
            )
        except ValueError:
            _logger.debug(
                "Cannot forward HID 0x%02X:0x%02X — unsupported usage",
                key_event.usage_page,
                key_event.usage,
            )
            return KeyEventDecision.SUPPRESS
        return KeyEventDecision.SUPPRESS

    def clear(self) -> None:
        self._suppressed_keyups.clear()
