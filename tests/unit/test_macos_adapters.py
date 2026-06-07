import pytest

from adapters.macos.keymap import KEYCODE_TO_VK, key_event_from_macos
from adapters.macos.permissions import AccessibilityPermissions
from interop.key.key_event import KeyEvent


def test_accessibility_permissions_returns_false_without_prompt():
    called = []

    def fake_checker(options):
        called.append(options)
        return False

    permissions = AccessibilityPermissions(checker=fake_checker)

    assert permissions.is_trusted(prompt=False) is False
    assert called == [None]


def test_accessibility_permissions_passes_prompt_option():
    called = []

    def fake_checker(options):
        called.append(options)
        return True

    permissions = AccessibilityPermissions(
        checker=fake_checker,
        prompt_key="prompt-key",
        true_value=True,
    )

    assert permissions.is_trusted(prompt=True) is True
    assert called == [{"prompt-key": True}]


def test_key_event_from_macos_maps_letter_keydown():
    event = key_event_from_macos(key_code=0, pressed=True, is_repeat=False)

    assert event == KeyEvent(vk=0x41, scan=0, extended=False, pressed=True)


def test_key_event_from_macos_maps_f11_keyup():
    event = key_event_from_macos(key_code=103, pressed=False, is_repeat=False)

    assert event == KeyEvent(vk=0x7A, scan=103, extended=False, pressed=False)


def test_key_event_from_macos_rejects_unknown_key_code():
    with pytest.raises(KeyError, match="Unsupported macOS key code 999"):
        key_event_from_macos(key_code=999, pressed=True, is_repeat=False)


def test_keycode_table_contains_f11_mapping():
    assert KEYCODE_TO_VK[103] == 0x7A
