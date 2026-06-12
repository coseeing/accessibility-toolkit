from interop.key import HID, KeyEvent
from apps.nvda_remote.legacy_key_payload import key_event_to_legacy_remote_payload


def test_hid_a_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 65,
        "scan_code": 30,
        "extended": False,
        "pressed": True,
    }


def test_hid_f11_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.F11, pressed=False)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 122,
        "scan_code": 87,
        "extended": False,
        "pressed": False,
    }


def test_hid_arrow_key_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.DOWN, pressed=True)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 40,
        "scan_code": 80,
        "extended": True,
        "pressed": True,
    }


def test_unsupported_usage_page_raises_value_error():
    event = KeyEvent(usage_page=0x0C, usage=0x01, pressed=True)
    try:
        key_event_to_legacy_remote_payload(event)
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_unsupported_usage_raises_value_error():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=0xFF, pressed=True)
    try:
        key_event_to_legacy_remote_payload(event)
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_hid_c_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.C, pressed=True)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 67,
        "scan_code": 46,
        "extended": False,
        "pressed": True,
    }


def test_hid_digit_1_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.DIGIT_1, pressed=False)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 49,
        "scan_code": 2,
        "extended": False,
        "pressed": False,
    }


def test_hid_backspace_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.BACKSPACE, pressed=True)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 8,
        "scan_code": 14,
        "extended": False,
        "pressed": True,
    }


def test_hid_left_meta_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.LEFT_META, pressed=True)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 91,
        "scan_code": 91,
        "extended": False,
        "pressed": True,
    }


def test_hid_f1_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.F1, pressed=True)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 112,
        "scan_code": 59,
        "extended": False,
        "pressed": True,
    }
