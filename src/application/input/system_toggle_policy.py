from adapters.inputs.captured_event import CapturedKeyEvent
from adapters.windows.native_key_context import WindowsNativeKeyContext
from interop.key import HID


def should_pass_through_system_toggle(event: CapturedKeyEvent) -> bool:
    return (
        event.key_event.usage == HID.NUM_LOCK
        and isinstance(event.native_context, WindowsNativeKeyContext)
    )
