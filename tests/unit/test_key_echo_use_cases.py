from interop.key.key_event import KeyEvent

from apps.key_echo.use_cases.state_transition_hotkeys import (
    KeyEchoHotkeyAction,
    KeyEchoStateTransitionHotkeyUseCase,
)


def test_key_echo_hotkey_use_case_maps_enter_to_start_echo():
    use_case = KeyEchoStateTransitionHotkeyUseCase(
        mapping={
            0x0D: KeyEchoHotkeyAction.START_ECHO,
            0x1B: KeyEchoHotkeyAction.STOP_ECHO,
        }
    )

    action = use_case.match(KeyEvent(vk=0x0D, scan=28, extended=False, pressed=True))

    assert action == KeyEchoHotkeyAction.START_ECHO


def test_key_echo_hotkey_use_case_maps_escape_to_stop_echo():
    use_case = KeyEchoStateTransitionHotkeyUseCase(
        mapping={
            0x0D: KeyEchoHotkeyAction.START_ECHO,
            0x1B: KeyEchoHotkeyAction.STOP_ECHO,
        }
    )

    action = use_case.match(KeyEvent(vk=0x1B, scan=1, extended=False, pressed=True))

    assert action == KeyEchoHotkeyAction.STOP_ECHO


def test_key_echo_hotkey_use_case_ignores_keyup():
    use_case = KeyEchoStateTransitionHotkeyUseCase(
        mapping={
            0x0D: KeyEchoHotkeyAction.START_ECHO,
            0x1B: KeyEchoHotkeyAction.STOP_ECHO,
        }
    )

    action = use_case.match(KeyEvent(vk=0x1B, scan=1, extended=False, pressed=False))

    assert action is None
