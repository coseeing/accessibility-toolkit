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
    54: 0x5C,  # RightCommand
    55: 0x5B,  # LeftCommand
    56: 0x10,  # LeftShift
    57: 0x14,  # CapsLock
    58: 0x12,  # LeftOption
    59: 0x11,  # LeftControl
    60: 0x10,  # RightShift
    61: 0x12,  # RightOption
    62: 0x11,  # RightControl
    65: 0x6E,  # KeypadDecimal
    67: 0x6A,  # KeypadMultiply
    69: 0x6B,  # KeypadPlus
    71: 0x0C,  # KeypadClear
    75: 0x6F,  # KeypadDivide
    76: 0x0D,  # NumpadEnter
    78: 0x6D,  # KeypadMinus
    81: 0xBB,  # KeypadEquals
    82: 0x60,  # Keypad0
    83: 0x61,  # Keypad1
    84: 0x62,  # Keypad2
    85: 0x63,  # Keypad3
    86: 0x64,  # Keypad4
    87: 0x65,  # Keypad5
    88: 0x66,  # Keypad6
    89: 0x67,  # Keypad7
    91: 0x68,  # Keypad8
    92: 0x69,  # Keypad9
    96: 0x74,  # F5
    97: 0x75,  # F6
    98: 0x76,  # F7
    99: 0x72,  # F3
    100: 0x77,  # F8
    101: 0x78,  # F9
    103: 0x7A,  # F11
    109: 0x79,  # F10
    111: 0x7B,  # F12
    114: 0x2D,  # Help/Insert
    115: 0x24,  # Home
    116: 0x21,  # PageUp
    117: 0x2E,  # ForwardDelete
    118: 0x73,  # F4
    119: 0x23,  # End
    120: 0x71,  # F2
    121: 0x22,  # PageDown
    122: 0x70,  # F1
    123: 0x25,  # LeftArrow
    124: 0x27,  # RightArrow
    125: 0x28,  # DownArrow
    126: 0x26,  # UpArrow
}

EXTENDED_KEY_CODES: set[int] = {
    114,
    115,
    116,
    117,
    119,
    121,
    123,
    124,
    125,
    126,
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
