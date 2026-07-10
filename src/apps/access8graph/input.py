from apps.access8graph.navigation.model import NavigationCommand
from accessibility_toolkit.input import HID
from accessibility_toolkit.input.events import KeyEvent


class Access8GraphKeyTranslator:
    _COMMAND_BY_USAGE = {
        HID.UP: NavigationCommand.UP,
        HID.DOWN: NavigationCommand.DOWN,
        HID.LEFT: NavigationCommand.LEFT,
        HID.RIGHT: NavigationCommand.RIGHT,
        HID.ENTER: NavigationCommand.CONFIRM,
        HID.KEYPAD_ENTER: NavigationCommand.CONFIRM,
        HID.HOME: NavigationCommand.HOME,
        HID.END: NavigationCommand.END,
        HID.D: NavigationCommand.SELECT_DIRECTION,
        HID.U: NavigationCommand.SELECT_UNDIRECTED,
        HID.P: NavigationCommand.SELECT_PLAN,
        HID.Q: NavigationCommand.QUIT,
        HID.H: NavigationCommand.OPEN_HELP,
        HID.M: NavigationCommand.OPEN_MODE,
        HID.V: NavigationCommand.OPEN_BROWSER,
        HID.S: NavigationCommand.SELECT_STATION,
        HID.L: NavigationCommand.SELECT_LINE,
        HID.E: NavigationCommand.SELECT_ENDPOINT,
    }

    def translate(self, event: KeyEvent) -> NavigationCommand | None:
        if event.usage_page != HID.KEYBOARD_PAGE or not event.pressed:
            return None
        return self._COMMAND_BY_USAGE.get(event.usage)
