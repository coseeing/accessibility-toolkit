from adapters.inputs.captured_event import CapturedKeyEvent
from adapters.windows.native_key_context import WindowsNativeKeyContext

from apps.nvda_remote.legacy_key_payload import key_event_to_legacy_remote_payload


def legacy_payload_from_captured_event(captured: CapturedKeyEvent) -> dict[str, int | bool]:
    context = captured.native_context
    if isinstance(context, WindowsNativeKeyContext):
        return {
            "vk_code": context.vk_code,
            "scan_code": context.scan_code,
            "extended": context.extended,
            "pressed": captured.key_event.pressed,
        }
    return key_event_to_legacy_remote_payload(captured.key_event)
