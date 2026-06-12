from interop.key import HID, KeyEvent

_USAGE_TO_LEGACY: dict[int, tuple[int, int, bool]] = {
    HID.A: (65, 30, False),
    HID.B: (66, 48, False),
    HID.ENTER: (13, 28, False),
    HID.ESCAPE: (27, 1, False),
    HID.TAB: (9, 15, False),
    HID.SPACE: (32, 57, False),
    HID.F11: (122, 87, False),
    HID.LEFT: (37, 75, True),
    HID.RIGHT: (39, 77, True),
    HID.UP: (38, 72, True),
    HID.DOWN: (40, 80, True),
    HID.LEFT_CONTROL: (17, 29, False),
    HID.RIGHT_CONTROL: (17, 29, True),
    HID.LEFT_SHIFT: (16, 42, False),
    HID.RIGHT_SHIFT: (16, 54, False),
    HID.LEFT_ALT: (18, 56, False),
    HID.RIGHT_ALT: (18, 56, True),
}


def key_event_to_legacy_remote_payload(event: KeyEvent) -> dict[str, int | bool]:
    if event.usage_page != HID.KEYBOARD_PAGE:
        raise ValueError(f"Unsupported HID usage page: 0x{event.usage_page:02X}")
    mapping = _USAGE_TO_LEGACY.get(event.usage)
    if mapping is None:
        raise ValueError(f"Unsupported HID usage for remote payload: 0x{event.usage:02X}")
    vk_code, scan_code, extended = mapping
    return {
        "vk_code": vk_code,
        "scan_code": scan_code,
        "extended": extended,
        "pressed": event.pressed,
    }
