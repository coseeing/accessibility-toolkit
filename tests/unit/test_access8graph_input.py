import pytest

from apps.access8graph.input import Access8GraphKeyTranslator
from apps.access8graph.navigation.model import NavigationCommand
from interop.key import HID, KeyEvent


@pytest.mark.parametrize(
    ("usage", "command"),
    [
        (HID.UP, NavigationCommand.UP),
        (HID.DOWN, NavigationCommand.DOWN),
        (HID.LEFT, NavigationCommand.LEFT),
        (HID.RIGHT, NavigationCommand.RIGHT),
        (HID.ENTER, NavigationCommand.CONFIRM),
        (HID.KEYPAD_ENTER, NavigationCommand.CONFIRM),
        (HID.HOME, NavigationCommand.HOME),
        (HID.END, NavigationCommand.END),
        (HID.D, NavigationCommand.SELECT_DIRECTION),
        (HID.U, NavigationCommand.SELECT_UNDIRECTED),
        (HID.P, NavigationCommand.SELECT_PLAN),
        (HID.Q, NavigationCommand.QUIT),
        (HID.H, NavigationCommand.OPEN_HELP),
        (HID.M, NavigationCommand.OPEN_MODE),
        (HID.V, NavigationCommand.OPEN_BROWSER),
        (HID.S, NavigationCommand.SELECT_STATION),
        (HID.L, NavigationCommand.SELECT_LINE),
        (HID.E, NavigationCommand.SELECT_ENDPOINT),
    ],
)
def test_translator_maps_supported_key_down_events(usage: int, command: NavigationCommand) -> None:
    translator = Access8GraphKeyTranslator()

    result = translator.translate(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=usage, pressed=True)
    )

    assert result is command


def test_translator_returns_none_for_escape_key() -> None:
    translator = Access8GraphKeyTranslator()

    result = translator.translate(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.ESCAPE, pressed=True)
    )

    assert result is None


def test_translator_ignores_key_up_events() -> None:
    translator = Access8GraphKeyTranslator()

    result = translator.translate(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.UP, pressed=False)
    )

    assert result is None


def test_translator_ignores_unsupported_keyboard_keys() -> None:
    translator = Access8GraphKeyTranslator()

    result = translator.translate(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)
    )

    assert result is None


def test_translator_ignores_non_keyboard_usage_page() -> None:
    translator = Access8GraphKeyTranslator()

    result = translator.translate(
        KeyEvent(usage_page=0x01, usage=HID.UP, pressed=True)
    )

    assert result is None
