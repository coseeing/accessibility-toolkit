from application.input.results import AppKeyEventResult
from interop.key import HID, KeyEvent

from application.input.active_key_policy import ActiveKeyEventPolicy


def test_active_key_policy_uses_exit_key_before_normal_handler():
    calls: list[str] = []
    policy = ActiveKeyEventPolicy(
        exit_usage=HID.ESCAPE,
        on_exit=lambda: calls.append("exit") or AppKeyEventResult.HANDLED_STOP,
        on_key=lambda event: calls.append(f"key:{event.usage}") or AppKeyEventResult.UNHANDLED,
    )

    exit_result = policy.handle(KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.ESCAPE, pressed=True))
    other_result = policy.handle(KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True))

    assert exit_result is AppKeyEventResult.HANDLED_STOP
    assert other_result is AppKeyEventResult.UNHANDLED
    assert calls == ["exit", f"key:{HID.A}"]


def test_active_key_policy_returns_unhandled_when_on_key_does_not_handle():
    policy = ActiveKeyEventPolicy(
        exit_usage=HID.ESCAPE,
        on_exit=lambda: AppKeyEventResult.HANDLED_STOP,
        on_key=lambda _event: AppKeyEventResult.UNHANDLED,
    )

    result = policy.handle(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)
    )

    assert result is AppKeyEventResult.UNHANDLED
