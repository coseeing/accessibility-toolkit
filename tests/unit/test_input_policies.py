from adapters.inputs.base import KeyEventDecision
from interop.key.key_event import KeyEvent

from application.input.active_key_policy import ActiveKeyEventPolicy
from application.input.state_transition_hotkeys import StateTransitionHotkeyPolicy


def test_idle_hotkey_policy_matches_keydown_only():
    policy = StateTransitionHotkeyPolicy(mapping={0x7A: "enter_active"})

    assert policy.match(KeyEvent(vk=0x7A, scan=87, extended=False, pressed=True)) == "enter_active"
    assert policy.match(KeyEvent(vk=0x7A, scan=87, extended=False, pressed=False)) is None


def test_active_key_policy_uses_exit_key_before_normal_handler():
    calls: list[str] = []
    policy = ActiveKeyEventPolicy(
        exit_vk=0x1B,
        on_exit=lambda: calls.append("exit") or KeyEventDecision.SUPPRESS,
        on_key=lambda event: calls.append(f"key:{event.vk}") or KeyEventDecision.PASS_THROUGH,
    )

    exit_decision = policy.handle(KeyEvent(vk=0x1B, scan=1, extended=False, pressed=True))
    other_decision = policy.handle(KeyEvent(vk=65, scan=30, extended=False, pressed=True))

    assert exit_decision == KeyEventDecision.SUPPRESS
    assert other_decision == KeyEventDecision.PASS_THROUGH
    assert calls == ["exit", "key:65"]
