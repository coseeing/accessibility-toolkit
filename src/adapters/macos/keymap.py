from interop.key import HID, KeyEvent
from adapters.macos.hid_map import KEYCODE_TO_USAGE


def key_event_from_macos(*, key_code: int, pressed: bool, is_repeat: bool) -> KeyEvent | None:
    del is_repeat
    usage = KEYCODE_TO_USAGE.get(key_code)
    if usage is None:
        return None
    return KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=usage, pressed=pressed)
