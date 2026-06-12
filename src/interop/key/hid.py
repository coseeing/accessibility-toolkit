from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class _HIDKeyboard:
    KEYBOARD_PAGE: int = 0x07
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
    ENTER: int = 0x28
    ESCAPE: int = 0x29
    BACKSPACE: int = 0x2A
    TAB: int = 0x2B
    SPACE: int = 0x2C
    MINUS: int = 0x2D
    EQUALS: int = 0x2E
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
    RIGHT: int = 0x4F
    LEFT: int = 0x50
    DOWN: int = 0x51
    UP: int = 0x52
    KEYPAD_ENTER: int = 0x58
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
