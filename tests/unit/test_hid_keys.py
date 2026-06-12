from interop.key import HID, KeyEvent


def test_key_event_uses_hid_fields():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)
    assert event.usage_page == 0x07
    assert event.usage == 0x04
    assert event.pressed is True


def test_key_event_to_local_payload_is_hid_first():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.F11, pressed=False)
    assert event.to_local_payload() == {
        "usage_page": 0x07,
        "usage": 0x44,
        "pressed": False,
    }
