from adapters.inputs.captured_event import CapturedKeyEvent
from adapters.windows.native_key_context import WindowsNativeKeyContext
from interop.key import HID, KeyEvent

from apps.nvda_remote.legacy_key_payload_bridge import legacy_payload_from_captured_event


def test_bridge_prefers_windows_native_context():
    captured = CapturedKeyEvent(
        key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True),
        native_context=WindowsNativeKeyContext(vk_code=0x41, scan_code=30, extended=False),
    )

    assert legacy_payload_from_captured_event(captured) == {
        "vk_code": 0x41,
        "scan_code": 30,
        "extended": False,
        "pressed": True,
    }


def test_bridge_falls_back_to_hid_when_native_context_is_none():
    captured = CapturedKeyEvent(
        key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True),
        native_context=None,
    )

    assert legacy_payload_from_captured_event(captured) == {
        "vk_code": 65,
        "scan_code": 30,
        "extended": False,
        "pressed": True,
    }
