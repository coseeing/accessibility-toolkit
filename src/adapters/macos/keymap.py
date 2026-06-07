from interop.key.key_event import KeyEvent


KEYCODE_TO_VK: dict[int, int] = {
    0: 0x41,  # A
    1: 0x53,  # S
    2: 0x44,  # D
    3: 0x46,  # F
    4: 0x48,  # H
    5: 0x47,  # G
    6: 0x5A,  # Z
    7: 0x58,  # X
    8: 0x43,  # C
    9: 0x56,  # V
    11: 0x42,  # B
    12: 0x51,  # Q
    13: 0x57,  # W
    14: 0x45,  # E
    15: 0x52,  # R
    16: 0x59,  # Y
    17: 0x54,  # T
    18: 0x31,  # 1
    19: 0x32,  # 2
    20: 0x33,  # 3
    21: 0x34,  # 4
    22: 0x36,  # 6
    23: 0x35,  # 5
    24: 0xBB,  # Equal
    25: 0x39,  # 9
    26: 0x37,  # 7
    27: 0xBD,  # Minus
    28: 0x38,  # 8
    29: 0x30,  # 0
    30: 0xDD,  # RightBracket
    31: 0x4F,  # O
    32: 0x55,  # U
    33: 0xDB,  # LeftBracket
    34: 0x49,  # I
    35: 0x50,  # P
    36: 0x0D,  # Return
    37: 0x4C,  # L
    38: 0x4A,  # J
    39: 0xDE,  # Quote
    40: 0x4B,  # K
    41: 0xBA,  # Semicolon
    42: 0xDC,  # Backslash
    43: 0xBC,  # Comma
    44: 0xBF,  # Slash
    45: 0x4E,  # N
    46: 0x4D,  # M
    47: 0xBE,  # Period
    48: 0x09,  # Tab
    49: 0x20,  # Space
    50: 0xC0,  # Grave
    51: 0x08,  # Backspace
    53: 0x1B,  # Escape
    54: 0x11,  # RightCommand
    55: 0x5B,  # LeftCommand
    56: 0x10,  # LeftShift
    57: 0x14,  # CapsLock
    58: 0x12,  # LeftOption
    59: 0x11,  # LeftControl
    60: 0x10,  # RightShift
    61: 0x12,  # RightOption
    62: 0x11,  # RightControl
    76: 0x0D,  # NumpadEnter
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
    116: 0x21,  # PageUp
    117: 0x2E,  # ForwardDelete
    123: 0x25,  # LeftArrow
    124: 0x27,  # RightArrow
    125: 0x28,  # DownArrow
    126: 0x26,  # UpArrow
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


def key_event_from_macos(
    *, key_code: int, pressed: bool, is_repeat: bool
) -> KeyEvent | None:
    del is_repeat
    vk = KEYCODE_TO_VK.get(key_code)
    if vk is None:
        return None
    return KeyEvent(
        vk=vk,
        scan=key_code,
        extended=key_code in EXTENDED_KEY_CODES,
        pressed=pressed,
    )
