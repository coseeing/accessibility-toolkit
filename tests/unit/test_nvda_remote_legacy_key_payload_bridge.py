from accessibility_toolkit.adapters.inputs.captured_event import CapturedKeyEvent
from accessibility_toolkit.adapters.windows.native_key_context import WindowsNativeKeyContext
from accessibility_toolkit.interop.key import HID, KeyEvent

from apps.nvda_remote.legacy_key_payload_bridge import legacy_payload_from_captured_event


def test_bridge_defaults_to_hid_conversion_even_with_windows_native_context():
    captured = CapturedKeyEvent(
        key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.KEYPAD_5, pressed=True),
        native_context=WindowsNativeKeyContext(vk_code=0x09, scan_code=15, extended=False),
        num_lock_on=False,
    )

    assert legacy_payload_from_captured_event(captured) == {
        "vk_code": 0x0C,
        "scan_code": 76,
        "extended": False,
        "pressed": True,
    }


def test_bridge_uses_windows_native_context_when_native_compatibility_mode_is_enabled():
    captured = CapturedKeyEvent(
        key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.KEYPAD_5, pressed=True),
        native_context=WindowsNativeKeyContext(vk_code=0x09, scan_code=15, extended=False),
        num_lock_on=False,
    )

    assert legacy_payload_from_captured_event(
        captured,
        use_windows_native_key_payload=True,
    ) == {
        "vk_code": 0x09,
        "scan_code": 15,
        "extended": False,
        "pressed": True,
    }


def test_bridge_falls_back_to_hid_conversion_when_native_mode_has_no_windows_context():
    captured = CapturedKeyEvent(
        key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.KEYPAD_5, pressed=True),
        native_context=None,
        num_lock_on=False,
    )

    assert legacy_payload_from_captured_event(
        captured,
        use_windows_native_key_payload=True,
    ) == {
        "vk_code": 0x0C,
        "scan_code": 76,
        "extended": False,
        "pressed": True,
    }
