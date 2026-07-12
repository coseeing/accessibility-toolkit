from accessibility_toolkit.input import (
    AppKeyEventResult,
    HID,
    KeyBinding,
    KeyChord,
    KeyEvent,
    KeyEventRouter,
    KeyTrigger,
    Modifier,
)


class FakeDelayedScheduler:
    def __init__(self) -> None:
        self.calls: list[tuple[float, object]] = []

    def schedule(self, delay_seconds, callback):
        call = FakeScheduledCall(callback)
        self.calls.append((delay_seconds, call))
        return call


class FalseyDelayedScheduler(FakeDelayedScheduler):
    def __bool__(self):
        return False


class FakeScheduledCall:
    def __init__(self, callback) -> None:
        self._callback = callback
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True

    def fire(self) -> None:
        if not self.cancelled:
            self._callback()


def key(usage: int, pressed: bool = True) -> KeyEvent:
    return KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=usage, pressed=pressed)


def test_router_dispatches_a_key_down_binding():
    calls = []
    router = KeyEventRouter(
        bindings=(
            KeyBinding(
                chord=KeyChord(HID.A),
                trigger=KeyTrigger.KEY_DOWN,
                handler=lambda event: calls.append(event) or AppKeyEventResult.HANDLED_STOP,
            ),
        )
    )

    result = router.handle(key(HID.A))

    assert result is AppKeyEventResult.HANDLED_STOP
    assert calls == [key(HID.A)]


def test_router_normalizes_left_and_right_control_for_exact_chord_matching():
    calls = []
    router = KeyEventRouter(
        bindings=(
            KeyBinding(
                chord=KeyChord(HID.S, modifiers=frozenset({Modifier.CONTROL})),
                trigger=KeyTrigger.KEY_DOWN,
                handler=lambda event: calls.append(event) or AppKeyEventResult.HANDLED_STOP,
            ),
        )
    )

    router.handle(key(HID.LEFT_CONTROL))
    result = router.handle(key(HID.S))
    router.handle(key(HID.S, pressed=False))
    router.handle(key(HID.LEFT_CONTROL, pressed=False))
    router.handle(key(HID.LEFT_CONTROL))
    router.handle(key(HID.LEFT_SHIFT))
    extra_modifier_result = router.handle(key(HID.S))

    assert result is AppKeyEventResult.HANDLED_STOP
    assert extra_modifier_result is AppKeyEventResult.UNHANDLED
    assert calls == [key(HID.S)]


def test_router_uses_fallback_for_an_unbound_event():
    calls = []
    router = KeyEventRouter(
        bindings=(),
        fallback=lambda event: calls.append(event) or AppKeyEventResult.HANDLED_CONTINUE,
    )

    result = router.handle(key(HID.A))

    assert result is AppKeyEventResult.HANDLED_CONTINUE
    assert calls == [key(HID.A)]


def test_long_press_uses_default_scheduler_when_none_is_injected(monkeypatch):
    created = []

    class FakeTimer:
        def __init__(self, seconds, callback):
            self.seconds = seconds
            self.callback = callback
            self.daemon = False
            self.started = False
            self.cancelled = False
            created.append(self)

        def start(self):
            self.started = True

        def cancel(self):
            self.cancelled = True

    monkeypatch.setattr("accessibility_toolkit.input.router.threading.Timer", FakeTimer)
    router = KeyEventRouter(
        bindings=(
            KeyBinding(
                chord=KeyChord(HID.A),
                trigger=KeyTrigger.LONG_PRESS,
                duration_seconds=1.25,
                handler=lambda _event: AppKeyEventResult.HANDLED_STOP,
            ),
        )
    )

    assert router.handle(key(HID.A)) is AppKeyEventResult.HANDLED_STOP
    assert created[0].seconds == 1.25
    assert created[0].daemon is True
    assert created[0].started is True


def test_long_press_uses_injected_scheduler_instead_of_threading_timer(monkeypatch):
    def unexpected_timer(*_args, **_kwargs):
        raise AssertionError("threading.Timer should not be used")

    monkeypatch.setattr(
        "accessibility_toolkit.input.router.threading.Timer", unexpected_timer
    )
    scheduler = FakeDelayedScheduler()
    router = KeyEventRouter(
        bindings=(
            KeyBinding(
                chord=KeyChord(HID.A),
                trigger=KeyTrigger.LONG_PRESS,
                duration_seconds=1.25,
                handler=lambda _event: AppKeyEventResult.HANDLED_STOP,
            ),
        ),
        delayed_scheduler=scheduler,
    )

    assert router.handle(key(HID.A)) is AppKeyEventResult.HANDLED_STOP
    assert scheduler.calls[0][0] == 1.25


def test_long_press_preserves_falsey_injected_scheduler(monkeypatch):
    def unexpected_timer(*_args, **_kwargs):
        raise AssertionError("threading.Timer should not be used")

    monkeypatch.setattr(
        "accessibility_toolkit.input.router.threading.Timer", unexpected_timer
    )
    scheduler = FalseyDelayedScheduler()
    router = KeyEventRouter(
        bindings=(
            KeyBinding(
                chord=KeyChord(HID.A),
                trigger=KeyTrigger.LONG_PRESS,
                duration_seconds=1.25,
                handler=lambda _event: AppKeyEventResult.HANDLED_STOP,
            ),
        ),
        delayed_scheduler=scheduler,
    )

    assert router.handle(key(HID.A)) is AppKeyEventResult.HANDLED_STOP
    assert scheduler.calls[0][0] == 1.25


def test_long_press_defers_key_down_until_key_is_released_before_deadline():
    calls = []
    scheduler = FakeDelayedScheduler()
    router = KeyEventRouter(
        bindings=(
            KeyBinding(
                chord=KeyChord(HID.A),
                trigger=KeyTrigger.KEY_DOWN,
                handler=lambda event: calls.append("down") or AppKeyEventResult.HANDLED_STOP,
            ),
            KeyBinding(
                chord=KeyChord(HID.A),
                trigger=KeyTrigger.LONG_PRESS,
                duration_seconds=1.5,
                handler=lambda event: calls.append("long") or AppKeyEventResult.HANDLED_STOP,
            ),
        ),
        delayed_scheduler=scheduler,
    )

    down_result = router.handle(key(HID.A))
    up_result = router.handle(key(HID.A, pressed=False))
    scheduler.calls[0][1].fire()

    assert down_result is AppKeyEventResult.HANDLED_STOP
    assert up_result is AppKeyEventResult.HANDLED_STOP
    assert scheduler.calls[0][0] == 1.5
    assert calls == ["down"]


def test_long_press_runs_at_deadline_without_running_delayed_key_down():
    calls = []
    scheduler = FakeDelayedScheduler()
    router = KeyEventRouter(
        bindings=(
            KeyBinding(
                chord=KeyChord(HID.A),
                trigger=KeyTrigger.KEY_DOWN,
                handler=lambda event: calls.append("down") or AppKeyEventResult.HANDLED_STOP,
            ),
            KeyBinding(
                chord=KeyChord(HID.A),
                trigger=KeyTrigger.LONG_PRESS,
                duration_seconds=1.5,
                handler=lambda event: calls.append("long") or AppKeyEventResult.HANDLED_STOP,
            ),
        ),
        delayed_scheduler=scheduler,
    )

    router.handle(key(HID.A))
    scheduler.calls[0][1].fire()
    router.handle(key(HID.A, pressed=False))

    assert calls == ["long"]


def test_long_press_handler_can_reset_router():
    scheduler = FakeDelayedScheduler()
    calls = []

    def reset_router(_event):
        calls.append("long")
        router.reset()
        return AppKeyEventResult.HANDLED_STOP

    router = KeyEventRouter(
        bindings=(
            KeyBinding(
                chord=KeyChord(HID.A),
                trigger=KeyTrigger.LONG_PRESS,
                duration_seconds=1.5,
                handler=reset_router,
            ),
        ),
        delayed_scheduler=scheduler,
    )

    router.handle(key(HID.A))
    scheduler.calls[0][1].fire()

    assert calls == ["long"]
    assert router._pending_long_presses == {}


def test_long_press_is_cancelled_when_its_modifier_is_released():
    calls = []
    scheduler = FakeDelayedScheduler()
    router = KeyEventRouter(
        bindings=(
            KeyBinding(
                chord=KeyChord(HID.A, modifiers=frozenset({Modifier.CONTROL})),
                trigger=KeyTrigger.LONG_PRESS,
                duration_seconds=1.5,
                handler=lambda event: calls.append(event) or AppKeyEventResult.HANDLED_STOP,
            ),
        ),
        delayed_scheduler=scheduler,
    )

    router.handle(key(HID.LEFT_CONTROL))
    router.handle(key(HID.A))
    router.handle(key(HID.LEFT_CONTROL, pressed=False))
    scheduler.calls[0][1].fire()

    assert scheduler.calls[0][1].cancelled is True
    assert calls == []
