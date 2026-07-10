import pytest

from accessibility_toolkit.input import HID, KeyEvent
from accessibility_toolkit.input.windows.hid_map import key_event_from_windows
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


@pytest.mark.parametrize(
    ("usage", "expected_on", "expected_off"),
    [
        (HID.KEYPAD_0, (0x60, 82, False), (0x2D, 82, False)),
        (HID.KEYPAD_1, (0x61, 79, False), (0x23, 79, False)),
        (HID.KEYPAD_2, (0x62, 80, False), (0x28, 80, False)),
        (HID.KEYPAD_3, (0x63, 81, False), (0x22, 81, False)),
        (HID.KEYPAD_4, (0x64, 75, False), (0x25, 75, False)),
        (HID.KEYPAD_5, (0x65, 76, False), (0x0C, 76, False)),
        (HID.KEYPAD_6, (0x66, 77, False), (0x27, 77, False)),
        (HID.KEYPAD_7, (0x67, 71, False), (0x24, 71, False)),
        (HID.KEYPAD_8, (0x68, 72, False), (0x26, 72, False)),
        (HID.KEYPAD_9, (0x69, 73, False), (0x21, 73, False)),
        (HID.KEYPAD_DECIMAL, (0x6E, 83, False), (0x2E, 83, False)),
    ],
)
def test_keypad_numeric_keys_map_by_num_lock_state(usage, expected_on, expected_off):
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=usage, pressed=True)

    assert key_event_to_legacy_remote_payload(event, num_lock_on=True) == {
        "vk_code": expected_on[0],
        "scan_code": expected_on[1],
        "extended": expected_on[2],
        "pressed": True,
    }
    assert key_event_to_legacy_remote_payload(event, num_lock_on=False) == {
        "vk_code": expected_off[0],
        "scan_code": expected_off[1],
        "extended": expected_off[2],
        "pressed": True,
    }


@pytest.mark.parametrize(
    ("usage", "expected"),
    [
        (HID.KEYPAD_DIVIDE, (0x6F, 53, True)),
        (HID.KEYPAD_MULTIPLY, (0x6A, 55, False)),
        (HID.KEYPAD_SUBTRACT, (0x6D, 74, False)),
        (HID.KEYPAD_ADD, (0x6B, 78, False)),
        (HID.KEYPAD_ENTER, (0x0D, 28, True)),
        (HID.KEYPAD_EQUALS, (0xBB, 89, False)),
    ],
)
def test_keypad_operator_keys_ignore_num_lock_state(usage, expected):
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=usage, pressed=False)

    assert key_event_to_legacy_remote_payload(event, num_lock_on=True) == {
        "vk_code": expected[0],
        "scan_code": expected[1],
        "extended": expected[2],
        "pressed": False,
    }
    assert key_event_to_legacy_remote_payload(event, num_lock_on=False) == {
        "vk_code": expected[0],
        "scan_code": expected[1],
        "extended": expected[2],
        "pressed": False,
    }


@pytest.mark.parametrize(
    ("vk_code", "scan_code", "extended", "num_lock_on"),
    [
        (0x6F, 53, True, None),
        (0x6A, 55, False, None),
        (0x6D, 74, False, None),
        (0x6B, 78, False, None),
        (0x0D, 28, True, None),
        (0xBB, 89, False, None),
        (0x60, 82, False, True),
        (0x61, 79, False, True),
        (0x62, 80, False, True),
        (0x63, 81, False, True),
        (0x64, 75, False, True),
        (0x65, 76, False, True),
        (0x66, 77, False, True),
        (0x67, 71, False, True),
        (0x68, 72, False, True),
        (0x69, 73, False, True),
        (0x6E, 83, False, True),
        (0x2D, 82, False, False),
        (0x23, 79, False, False),
        (0x28, 80, False, False),
        (0x22, 81, False, False),
        (0x25, 75, False, False),
        (0x0C, 76, False, False),
        (0x27, 77, False, False),
        (0x24, 71, False, False),
        (0x26, 72, False, False),
        (0x21, 73, False, False),
        (0x2E, 83, False, False),
    ],
)
def test_windows_keypad_hid_payload_preserves_scan_and_extended(
    vk_code,
    scan_code,
    extended,
    num_lock_on,
):
    event = key_event_from_windows(
        vk_code=vk_code,
        scan_code=scan_code,
        extended=extended,
        pressed=True,
    )

    assert event is not None
    payload = key_event_to_legacy_remote_payload(event, num_lock_on=num_lock_on)
    assert (payload["scan_code"], payload["extended"]) == (scan_code, extended)


def test_keypad_operator_key_preserves_mapping_when_num_lock_state_unknown():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.KEYPAD_DIVIDE, pressed=False)

    assert key_event_to_legacy_remote_payload(event, num_lock_on=None) == {
        "vk_code": 0x6F,
        "scan_code": 53,
        "extended": True,
        "pressed": False,
    }


def test_keypad_num_lock_none_preserves_existing_mapping():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.KEYPAD_2, pressed=True)

    assert key_event_to_legacy_remote_payload(event, num_lock_on=None) == {
        "vk_code": 0x62,
        "scan_code": 80,
        "extended": False,
        "pressed": True,
    }


def test_num_lock_state_must_be_passed_by_keyword():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.KEYPAD_2, pressed=True)

    with pytest.raises(TypeError):
        key_event_to_legacy_remote_payload(event, False)


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
