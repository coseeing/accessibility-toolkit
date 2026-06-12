from interop.key import HID, KeyEvent

_SCAN_TO_USAGE: dict[tuple[int, bool], int] = {
    (1, False): HID.ESCAPE,
    (15, False): HID.TAB,
    (28, False): HID.ENTER,
    (28, True): HID.KEYPAD_ENTER,
    (30, False): HID.A,
    (48, False): HID.B,
    (50, False): HID.M,
    (57, False): HID.SPACE,
    (59, False): HID.F1,
    (60, False): HID.F2,
    (61, False): HID.F3,
    (62, False): HID.F4,
    (63, False): HID.F5,
    (64, False): HID.F6,
    (65, False): HID.F7,
    (66, False): HID.F8,
    (67, False): HID.F9,
    (68, False): HID.F10,
    (87, False): HID.F11,
    (88, False): HID.F12,
    (72, True): HID.UP,
    (75, True): HID.LEFT,
    (77, True): HID.RIGHT,
    (80, True): HID.DOWN,
    (29, False): HID.LEFT_CONTROL,
    (29, True): HID.RIGHT_CONTROL,
    (42, False): HID.LEFT_SHIFT,
    (54, False): HID.RIGHT_SHIFT,
    (56, False): HID.LEFT_ALT,
    (56, True): HID.RIGHT_ALT,
    (91, False): HID.LEFT_META,
    (92, False): HID.RIGHT_META,
}


def key_event_from_windows(*, vk_code: int, scan_code: int, extended: bool, pressed: bool) -> KeyEvent | None:
    del vk_code
    usage = _SCAN_TO_USAGE.get((scan_code, extended))
    if usage is None:
        return None
    return KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=usage, pressed=pressed)
