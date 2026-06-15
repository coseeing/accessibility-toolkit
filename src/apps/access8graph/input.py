from interop.key import HID
from interop.key.key_event import KeyEvent


class Access8GraphKeyTranslator:
    _COMMAND_BY_USAGE = {
        HID.UP: "up",
        HID.DOWN: "down",
        HID.LEFT: "left",
        HID.RIGHT: "right",
        HID.ENTER: "enter",
        HID.KEYPAD_ENTER: "enter",
        HID.ESCAPE: "escape",
        HID.HOME: "home",
        HID.END: "end",
        HID.D: "d",
        HID.U: "u",
        HID.P: "p",
        HID.Q: "q",
        HID.H: "h",
        HID.M: "m",
        HID.V: "v",
        HID.S: "s",
        HID.L: "l",
        HID.E: "e",
    }

    def translate(self, event: KeyEvent) -> dict[str, int | str] | None:
        if event.usage_page != HID.KEYBOARD_PAGE or not event.pressed:
            return None
        command = self._COMMAND_BY_USAGE.get(event.usage)
        if command is None:
            return None
        return {
            "key": command,
            "repeat": 0,
            "pressing": 0,
        }
