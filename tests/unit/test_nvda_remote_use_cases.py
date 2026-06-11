from interop.key.key_event import KeyEvent

from apps.nvda_remote.use_cases.state_transition_hotkeys import (
    NvdaRemoteHotkeyAction,
    NvdaRemoteStateTransitionHotkeyUseCase,
)


def test_nvda_hotkey_use_case_maps_f11_keydown_to_toggle_control():
    use_case = NvdaRemoteStateTransitionHotkeyUseCase(
        mapping={0x7A: NvdaRemoteHotkeyAction.TOGGLE_CONTROL}
    )

    action = use_case.match(KeyEvent(vk=0x7A, scan=87, extended=False, pressed=True))

    assert action == NvdaRemoteHotkeyAction.TOGGLE_CONTROL


def test_nvda_hotkey_use_case_ignores_f11_keyup():
    use_case = NvdaRemoteStateTransitionHotkeyUseCase(
        mapping={0x7A: NvdaRemoteHotkeyAction.TOGGLE_CONTROL}
    )

    action = use_case.match(KeyEvent(vk=0x7A, scan=87, extended=False, pressed=False))

    assert action is None
