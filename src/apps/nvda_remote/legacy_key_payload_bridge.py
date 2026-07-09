from accessibility_toolkit.adapters.inputs.captured_event import CapturedKeyEvent
from accessibility_toolkit.adapters.windows.native_key_context import WindowsNativeKeyContext

from apps.nvda_remote.legacy_key_payload import key_event_to_legacy_remote_payload


def legacy_payload_from_captured_event(
    captured: CapturedKeyEvent,
    *,
    use_windows_native_key_payload: bool = False,
) -> dict[str, int | bool]:
    if use_windows_native_key_payload and isinstance(captured.native_context, WindowsNativeKeyContext):
        context = captured.native_context
        return {
            "vk_code": context.vk_code,
            "scan_code": context.scan_code,
            "extended": context.extended,
            "pressed": captured.key_event.pressed,
        }
    return key_event_to_legacy_remote_payload(captured.key_event, num_lock_on=captured.num_lock_on)
