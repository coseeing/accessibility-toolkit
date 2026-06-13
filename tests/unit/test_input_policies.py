from adapters.inputs.base import KeyEventDecision
from interop.key import HID, KeyEvent

from application.input.active_key_policy import ActiveKeyEventPolicy


def test_active_key_policy_uses_exit_key_before_normal_handler():
    calls: list[str] = []
    policy = ActiveKeyEventPolicy(
        exit_usage=HID.ESCAPE,
        on_exit=lambda: calls.append("exit") or KeyEventDecision.SUPPRESS,
        on_key=lambda event: calls.append(f"key:{event.usage}") or KeyEventDecision.PASS_THROUGH,
    )

    exit_decision = policy.handle(KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.ESCAPE, pressed=True))
    other_decision = policy.handle(KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True))

    assert exit_decision == KeyEventDecision.SUPPRESS
    assert other_decision == KeyEventDecision.PASS_THROUGH
    assert calls == ["exit", f"key:{HID.A}"]
