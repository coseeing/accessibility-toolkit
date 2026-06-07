from interop.key.key_event import KeyEvent


KEYCODE_TO_VK: dict[int, int] = {
    0: 0x41,  # A
    1: 0x53,  # S
    2: 0x44,  # D
    3: 0x46,  # F
    12: 0x51,  # Q
    13: 0x57,  # W
    14: 0x45,  # E
    15: 0x52,  # R
    17: 0x54,  # T
    31: 0x4F,  # O
    32: 0x55,  # U
    34: 0x49,  # I
    35: 0x50,  # P
    37: 0x4C,  # L
    38: 0x4A,  # J
    40: 0x4B,  # K
    45: 0x4E,  # N
    46: 0x4D,  # M
    49: 0x20,  # Space
    53: 0x1B,  # Escape
    76: 0x0D,  # Return
    96: 0x74,  # F5
    97: 0x2E,  # Delete
    98: 0x73,  # F4
    99: 0x24,  # Home
    100: 0x23,  # End
    101: 0x22,  # PageDown
    103: 0x7A,  # F11
    105: 0x25,  # Left
    106: 0x27,  # Right
    107: 0x28,  # Down
    108: 0x26,  # Up
    109: 0x70,  # F1
    111: 0x7B,  # F12
}

EXTENDED_KEY_CODES: set[int] = {
    96,
    97,
    99,
    100,
    101,
    105,
    106,
    107,
    108,
    109,
    111,
}


def key_event_from_macos(*, key_code: int, pressed: bool, is_repeat: bool) -> KeyEvent:
    del is_repeat
    try:
        vk = KEYCODE_TO_VK[key_code]
    except KeyError as error:
        raise KeyError(f"Unsupported macOS key code {key_code}") from error
    return KeyEvent(
        vk=vk,
        scan=key_code,
        extended=key_code in EXTENDED_KEY_CODES,
        pressed=pressed,
    )
