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
        "extended": True,
        "pressed": True,
    }


def test_hid_right_meta_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.RIGHT_META, pressed=False)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 92,
        "scan_code": 92,
        "extended": True,
        "pressed": False,
    }


def test_hid_f1_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.F1, pressed=True)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 112,
        "scan_code": 59,
        "extended": False,
        "pressed": True,
    }


def test_hid_minus_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.MINUS, pressed=True)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 189,
        "scan_code": 12,
        "extended": False,
        "pressed": True,
    }


def test_hid_equals_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.EQUALS, pressed=True)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 187,
        "scan_code": 13,
        "extended": False,
        "pressed": True,
    }


def test_hid_semicolon_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.SEMICOLON, pressed=True)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 186,
        "scan_code": 39,
        "extended": False,
        "pressed": True,
    }


def test_hid_page_down_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.PAGE_DOWN, pressed=False)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 34,
        "scan_code": 81,
        "extended": True,
        "pressed": False,
    }


def test_hid_keypad_1_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.KEYPAD_1, pressed=True)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 97,
        "scan_code": 79,
        "extended": False,
        "pressed": True,
    }


def test_hid_keypad_divide_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.KEYPAD_DIVIDE, pressed=True)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 111,
        "scan_code": 53,
        "extended": True,
        "pressed": True,
    }


def test_non_us_backslash_is_explicitly_unsupported_for_legacy_remote_payload():
    event = KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.NON_US_BACKSLASH,
        pressed=True,
    )
    try:
        key_event_to_legacy_remote_payload(event)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "NON_US_BACKSLASH" in str(exc)


def test_print_screen_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.PRINT_SCREEN, pressed=True)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 44,
        "scan_code": 55,
        "extended": True,
        "pressed": True,
    }


def test_scroll_lock_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.SCROLL_LOCK, pressed=False)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 145,
        "scan_code": 70,
        "extended": False,
        "pressed": False,
    }


def test_num_lock_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.NUM_LOCK, pressed=True)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 144,
        "scan_code": 69,
        "extended": True,
        "pressed": True,
    }


def test_application_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.APPLICATION, pressed=True)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 93,
        "scan_code": 93,
        "extended": True,
        "pressed": True,
    }


def test_pause_is_explicitly_unsupported_for_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.PAUSE, pressed=True)
    try:
        key_event_to_legacy_remote_payload(event)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "PAUSE" in str(exc)


def test_jis_keys_are_explicitly_unsupported_for_legacy_remote_payload():
    for usage_name, usage in [
        ("NON_US_HASH", HID.NON_US_HASH),
        ("INTERNATIONAL1", HID.INTERNATIONAL1),
        ("INTERNATIONAL3", HID.INTERNATIONAL3),
        ("INTERNATIONAL4", HID.INTERNATIONAL4),
        ("INTERNATIONAL5", HID.INTERNATIONAL5),
    ]:
        try:
            key_event_to_legacy_remote_payload(
                KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=usage, pressed=True)
            )
            assert False, f"Expected ValueError for {usage_name}"
        except ValueError as exc:
            assert usage_name in str(exc)


def test_raw_windows_values_take_priority_over_hid_lookup():
    event = KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.KEYPAD_1,
        pressed=True,
        vk=35,
        scan=79,
        extended=True,
    )
    payload = key_event_to_legacy_remote_payload(event)
    assert payload == {
        "vk_code": 35,
        "scan_code": 79,
        "extended": True,
        "pressed": True,
    }


def test_raw_windows_values_preserve_exact_scan_code():
    event = KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=0,
        pressed=True,
        vk=35,
        scan=57423,
        extended=True,
    )
    payload = key_event_to_legacy_remote_payload(event)
    assert payload == {
        "vk_code": 35,
        "scan_code": 57423,
        "extended": True,
        "pressed": True,
    }
