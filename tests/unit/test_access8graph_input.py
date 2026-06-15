import pytest

from apps.access8graph.input import Access8GraphKeyTranslator
from interop.key import HID, KeyEvent


@pytest.mark.parametrize(
    ("usage", "command"),
    [
        (HID.UP, "up"),
        (HID.DOWN, "down"),
        (HID.LEFT, "left"),
        (HID.RIGHT, "right"),
        (HID.ENTER, "enter"),
        (HID.KEYPAD_ENTER, "enter"),
        (HID.ESCAPE, "escape"),
        (HID.HOME, "home"),
        (HID.END, "end"),
        (HID.D, "d"),
        (HID.U, "u"),
        (HID.P, "p"),
        (HID.Q, "q"),
        (HID.H, "h"),
        (HID.M, "m"),
        (HID.V, "v"),
        (HID.S, "s"),
        (HID.L, "l"),
        (HID.E, "e"),
    ],
)
def test_translator_maps_supported_key_down_events(usage: int, command: str) -> None:
    translator = Access8GraphKeyTranslator()

    result = translator.translate(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=usage, pressed=True)
    )

    assert result == {
        "key": command,
        "repeat": 0,
        "pressing": 0,
    }


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
