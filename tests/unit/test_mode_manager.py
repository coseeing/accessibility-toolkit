from adapters.inputs.base import KeyEventDecision
from interop.key.key_event import KeyEvent

from apps.shared.mode_manager import ModeManager


class FakeActivation:
    def __init__(self):
        self.entered = 0
        self.exited = 0
        self.active = False

    def enter_active(self) -> bool:
        if self.active:
            return True
        self.entered += 1
        self.active = True
        return True

    def exit_active(self) -> bool:
        if not self.active:
            return True
        self.exited += 1
        self.active = False
        return True


class FakeMode:
    def __init__(self):
        self.entered = 0
        self.exited = 0
        self.events = []

    mode_id = "echo"
    enter_hotkey = "enter"
    exit_hotkey = 27

    def can_enter(self):
        return True

    def enter(self):
        self.entered += 1
        return True

    def exit(self):
        self.exited += 1
        return True

    def handle_key_event(self, event):
        self.events.append(event.vk)
        return KeyEventDecision.SUPPRESS


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
    assert statuses == [{"kind": "mode", "mode_id": "echo", "state": "active"}]


def test_mode_manager_routes_non_exit_keys_to_active_mode():
    mode = FakeMode()
    activation = FakeActivation()
    manager = ModeManager(
        activation=activation,
        notify_status=lambda _: None,
    )
    manager.register(mode)
    manager.activate_mode("echo")

    decision = manager.handle_key_event(
        KeyEvent(vk=65, scan=0, extended=False, pressed=True)
    )

    assert decision == KeyEventDecision.SUPPRESS
    assert mode.events == [65]


def test_mode_manager_exit_key_deactivates_mode():
    mode = FakeMode()
    activation = FakeActivation()
    statuses = []
    manager = ModeManager(
        activation=activation,
        notify_status=statuses.append,
    )
    manager.register(mode)
    manager.activate_mode("echo")

    decision = manager.handle_key_event(
        KeyEvent(vk=27, scan=1, extended=False, pressed=True)
    )

    assert decision == KeyEventDecision.SUPPRESS
    assert mode.exited == 1
    assert manager.active_mode_id is None
    assert statuses == [
        {"kind": "mode", "mode_id": "echo", "state": "active"},
        {"kind": "mode", "mode_id": "echo", "state": "idle"},
    ]


def test_mode_manager_passes_through_when_no_mode_active():
    activation = FakeActivation()
    manager = ModeManager(
        activation=activation,
        notify_status=lambda _: None,
    )

    decision = manager.handle_key_event(
        KeyEvent(vk=65, scan=0, extended=False, pressed=True)
    )

    assert decision == KeyEventDecision.PASS_THROUGH


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


def test_mode_manager_ignores_exit_key_release():
    mode = FakeMode()
    activation = FakeActivation()
    manager = ModeManager(
        activation=activation,
        notify_status=lambda _: None,
    )
    manager.register(mode)
    manager.activate_mode("echo")

    decision = manager.handle_key_event(
        KeyEvent(vk=27, scan=1, extended=False, pressed=False)
    )

    assert decision == KeyEventDecision.SUPPRESS
    assert mode.events == [27]
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
