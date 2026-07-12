from accessibility_toolkit.events import ModeChanged
from accessibility_toolkit.input import (
    AppKeyEventResult,
    HID,
    KeyBinding,
    KeyChord,
    KeyEvent,
    KeyEventRouter,
    KeyTrigger,
)

from accessibility_toolkit.interaction import ModeManager


class FakeActivation:
    def __init__(self):
        self.entered = 0
        self.exited = 0
        self.active = False
        self.fail_exit = False

    def enter_active(self) -> bool:
        if self.active:
            return True
        self.entered += 1
        self.active = True
        return True

    def exit_active(self) -> bool:
        if not self.active:
            return True
        if self.fail_exit:
            return False
        self.exited += 1
        self.active = False
        return True


class FakeMode:
    def __init__(self):
        self.entered = 0
        self.exited = 0
        self.events = []
        self.key_router = KeyEventRouter(bindings=(), fallback=self._handle_event)

    mode_id = "echo"
    enter_usage = HID.ENTER

    def can_enter(self):
        return True

    def enter(self):
        self.entered += 1
        return True

    def exit(self):
        self.exited += 1
        return True

    def _handle_event(self, event):
        self.events.append(event.usage)
        return AppKeyEventResult.HANDLED_STOP


def test_mode_manager_enters_mode_on_activation():
    mode = FakeMode()
    activation = FakeActivation()
    statuses = []
    manager = ModeManager(
        activation=activation,
        notify_status=statuses.append,
    )
    manager.register(mode)

    result = manager.activate_mode("echo")

    assert result is True
    assert mode.entered == 1
    assert manager.active_mode_id == "echo"
    assert statuses == [ModeChanged("echo", active=True)]


def test_mode_manager_routes_events_to_active_mode_router():
    mode = FakeMode()
    activation = FakeActivation()
    manager = ModeManager(
        activation=activation,
        notify_status=lambda _: None,
    )
    manager.register(mode)
    manager.activate_mode("echo")

    decision = manager.handle_key_event(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)
    )

    assert decision is AppKeyEventResult.HANDLED_STOP
    assert mode.events == [HID.A]


def test_mode_router_binding_can_deactivate_active_mode():
    mode = FakeMode()
    activation = FakeActivation()
    statuses = []
    manager = ModeManager(
        activation=activation,
        notify_status=statuses.append,
    )
    mode.key_router = KeyEventRouter(
        bindings=(
            KeyBinding(
                chord=KeyChord(HID.ESCAPE),
                trigger=KeyTrigger.KEY_DOWN,
                handler=lambda _event: manager.exit_active_mode(),
            ),
        )
    )
    manager.register(mode)
    manager.activate_mode("echo")

    decision = manager.handle_key_event(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.ESCAPE, pressed=True)
    )

    assert decision is AppKeyEventResult.HANDLED_STOP
    assert mode.exited == 1
    assert manager.active_mode_id is None
    assert statuses == [
        ModeChanged("echo", active=True),
        ModeChanged("echo", active=False),
    ]


def test_mode_manager_passes_through_when_no_mode_active():
    activation = FakeActivation()
    manager = ModeManager(
        activation=activation,
        notify_status=lambda _: None,
    )

    decision = manager.handle_key_event(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)
    )

    assert decision is AppKeyEventResult.UNHANDLED


def test_mode_manager_rejects_activation_when_cannot_enter():
    mode = FakeMode()
    mode.can_enter = lambda: False
    activation = FakeActivation()
    manager = ModeManager(
        activation=activation,
        notify_status=lambda _: None,
    )
    manager.register(mode)

    result = manager.activate_mode("echo")

    assert result is False
    assert mode.entered == 0
    assert manager.active_mode_id is None


def test_mode_manager_single_active_mode_guarantee():
    mode1 = FakeMode()
    mode1.mode_id = "echo"
    mode2 = FakeMode()
    mode2.mode_id = "remote"
    activation = FakeActivation()
    manager = ModeManager(
        activation=activation,
        notify_status=lambda _: None,
    )
    manager.register(mode1)
    manager.register(mode2)
    manager.activate_mode("echo")

    result = manager.activate_mode("remote")

    assert result is False
    assert manager.active_mode_id == "echo"


def test_mode_manager_routes_key_release_to_mode_router():
    mode = FakeMode()
    activation = FakeActivation()
    manager = ModeManager(
        activation=activation,
        notify_status=lambda _: None,
    )
    manager.register(mode)
    manager.activate_mode("echo")

    decision = manager.handle_key_event(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.ESCAPE, pressed=False)
    )

    assert decision is AppKeyEventResult.HANDLED_STOP
    assert mode.events == [HID.ESCAPE]
    assert manager.active_mode_id == "echo"


def test_mode_manager_handles_activate_rollback_on_enter_failure():
    mode = FakeMode()
    mode.enter = lambda: False
    activation = FakeActivation()
    manager = ModeManager(
        activation=activation,
        notify_status=lambda _: None,
    )
    manager.register(mode)

    result = manager.activate_mode("echo")

    assert result is False
    assert activation.active is False
    assert manager.active_mode_id is None


def test_mode_manager_preserves_active_mode_when_router_exit_handler_fails():
    mode = FakeMode()
    activation = FakeActivation()
    activation.fail_exit = True
    statuses = []
    manager = ModeManager(
        activation=activation,
        notify_status=statuses.append,
    )
    mode.key_router = KeyEventRouter(
        bindings=(
            KeyBinding(
                chord=KeyChord(HID.ESCAPE),
                trigger=KeyTrigger.KEY_DOWN,
                handler=lambda _event: manager.exit_active_mode(),
            ),
        )
    )
    manager.register(mode)
    manager.activate_mode("echo")

    decision = manager.handle_key_event(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.ESCAPE, pressed=True)
    )

    assert decision is AppKeyEventResult.HANDLED_STOP
    assert mode.exited == 0
    assert manager.active_mode_id == "echo"


def test_mode_manager_returns_unhandled_when_no_mode_is_active():
    manager = ModeManager(
        activation=FakeActivation(),
        notify_status=lambda _status: None,
    )

    result = manager.handle_key_event(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)
    )

    assert result is AppKeyEventResult.UNHANDLED
