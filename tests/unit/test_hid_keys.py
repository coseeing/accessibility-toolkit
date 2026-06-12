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


def test_hid_constants_cover_main_cluster_punctuation_navigation_and_numpad():
    assert HID.SEMICOLON == 0x33
    assert HID.QUOTE == 0x34
    assert HID.GRAVE == 0x35
    assert HID.COMMA == 0x36
    assert HID.PERIOD == 0x37
    assert HID.SLASH == 0x38
    assert HID.CAPS_LOCK == 0x39
    assert HID.INSERT == 0x49
    assert HID.HOME == 0x4A
    assert HID.PAGE_UP == 0x4B
    assert HID.DELETE == 0x4C
    assert HID.END == 0x4D
    assert HID.PAGE_DOWN == 0x4E
    assert HID.KEYPAD_DIVIDE == 0x54
    assert HID.KEYPAD_MULTIPLY == 0x55
    assert HID.KEYPAD_SUBTRACT == 0x56
    assert HID.KEYPAD_ADD == 0x57
    assert HID.KEYPAD_1 == 0x59
    assert HID.KEYPAD_0 == 0x62
    assert HID.KEYPAD_DECIMAL == 0x63
    assert HID.NON_US_BACKSLASH == 0x64
    assert HID.KEYPAD_EQUALS == 0x67


def test_hid_distinguishes_main_cluster_from_numpad_keys():
    assert HID.ENTER != HID.KEYPAD_ENTER
    assert HID.DIGIT_1 != HID.KEYPAD_1
    assert HID.SLASH != HID.KEYPAD_DIVIDE
    assert HID.PERIOD != HID.KEYPAD_DECIMAL
