from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class _HIDKeyboard:
    KEYBOARD_PAGE: int = 0x07

    # Alphanumeric
    A: int = 0x04
    B: int = 0x05
    C: int = 0x06
    D: int = 0x07
    E: int = 0x08
    F: int = 0x09
    G: int = 0x0A
    H: int = 0x0B
    I: int = 0x0C
    J: int = 0x0D
    K: int = 0x0E
    L: int = 0x0F
    M: int = 0x10
    N: int = 0x11
    O: int = 0x12
    P: int = 0x13
    Q: int = 0x14
    R: int = 0x15
    S: int = 0x16
    T: int = 0x17
    U: int = 0x18
    V: int = 0x19
    W: int = 0x1A
    X: int = 0x1B
    Y: int = 0x1C
    Z: int = 0x1D
    DIGIT_1: int = 0x1E
    DIGIT_2: int = 0x1F
    DIGIT_3: int = 0x20
    DIGIT_4: int = 0x21
    DIGIT_5: int = 0x22
    DIGIT_6: int = 0x23
    DIGIT_7: int = 0x24
    DIGIT_8: int = 0x25
    DIGIT_9: int = 0x26
    DIGIT_0: int = 0x27

    # Core controls and main-cluster punctuation
    ENTER: int = 0x28
    ESCAPE: int = 0x29
    BACKSPACE: int = 0x2A
    TAB: int = 0x2B
    SPACE: int = 0x2C
    MINUS: int = 0x2D
    EQUALS: int = 0x2E
    LEFT_BRACKET: int = 0x2F
    RIGHT_BRACKET: int = 0x30
    BACKSLASH: int = 0x31
    NON_US_HASH: int = 0x32
    SEMICOLON: int = 0x33
    QUOTE: int = 0x34
    GRAVE: int = 0x35
    COMMA: int = 0x36
    PERIOD: int = 0x37
    SLASH: int = 0x38
    CAPS_LOCK: int = 0x39

    # Function keys
    F1: int = 0x3A
    F2: int = 0x3B
    F3: int = 0x3C
    F4: int = 0x3D
    F5: int = 0x3E
    F6: int = 0x3F
    F7: int = 0x40
    F8: int = 0x41
    F9: int = 0x42
    F10: int = 0x43
    F11: int = 0x44
    F12: int = 0x45

    # Special control keys
    PRINT_SCREEN: int = 0x46
    SCROLL_LOCK: int = 0x47
    PAUSE: int = 0x48

    # Navigation and editing
    INSERT: int = 0x49
    HOME: int = 0x4A
    PAGE_UP: int = 0x4B
    DELETE: int = 0x4C
    END: int = 0x4D
    PAGE_DOWN: int = 0x4E
    RIGHT: int = 0x4F
    LEFT: int = 0x50
    DOWN: int = 0x51
    UP: int = 0x52
    NUM_LOCK: int = 0x53

    # Numpad
    KEYPAD_DIVIDE: int = 0x54
    KEYPAD_MULTIPLY: int = 0x55
    KEYPAD_SUBTRACT: int = 0x56
    KEYPAD_ADD: int = 0x57
    KEYPAD_ENTER: int = 0x58
    KEYPAD_1: int = 0x59
    KEYPAD_2: int = 0x5A
    KEYPAD_3: int = 0x5B
    KEYPAD_4: int = 0x5C
    KEYPAD_5: int = 0x5D
    KEYPAD_6: int = 0x5E
    KEYPAD_7: int = 0x5F
    KEYPAD_8: int = 0x60
    KEYPAD_9: int = 0x61
    KEYPAD_0: int = 0x62
    KEYPAD_DECIMAL: int = 0x63
    NON_US_BACKSLASH: int = 0x64
    APPLICATION: int = 0x65
    KEYPAD_EQUALS: int = 0x67

    # International / JIS
    INTERNATIONAL1: int = 0x87
    INTERNATIONAL3: int = 0x89
    INTERNATIONAL4: int = 0x8A
    INTERNATIONAL5: int = 0x8B

    # Modifiers
    LEFT_CONTROL: int = 0xE0
    LEFT_SHIFT: int = 0xE1
    LEFT_ALT: int = 0xE2
    LEFT_META: int = 0xE3
    RIGHT_CONTROL: int = 0xE4
    RIGHT_SHIFT: int = 0xE5
    RIGHT_ALT: int = 0xE6
    RIGHT_META: int = 0xE7

    def is_keyboard_page(self, usage_page: int) -> bool:
        return usage_page == self.KEYBOARD_PAGE


HID = _HIDKeyboard()
