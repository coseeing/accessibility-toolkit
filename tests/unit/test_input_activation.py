import logging

from accessibility_toolkit.input import InputActivationUseCase


class FakeCapture:
    def __init__(self, running: bool = False, fail_start: bool = False) -> None:
        self._running = running
        self._fail_start = fail_start
        self.started = 0
        self.stopped = 0

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> None:
        self.started += 1
        if self._fail_start:
            raise RuntimeError("boom")
        self._running = True

    def stop(self) -> None:
        self.stopped += 1
        self._running = False


class FakeSharedTap:
    def __init__(self) -> None:
        self.active_registrations = 0
        self.starts = 0
        self.stops = 0

    def register(self) -> None:
        if self.active_registrations == 0:
            self.starts += 1
        self.active_registrations += 1

    def unregister(self) -> None:
        self.active_registrations -= 1
        if self.active_registrations == 0:
            self.stops += 1


class SharedCapture:
    def __init__(self, manager: FakeSharedTap, *, running: bool = False) -> None:
        self._manager = manager
        self._running = False
        self.started = 0
        self.stopped = 0
        if running:
            self.start()

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> None:
        self.started += 1
        if self._running:
            return
        self._manager.register()
        self._running = True

    def stop(self) -> None:
        self.stopped += 1
        if not self._running:
            return
        self._manager.unregister()
        self._running = False


def test_activation_enters_active_by_stopping_hotkey_and_starting_keyboard():
    keyboard = FakeCapture(running=False)
    hotkey = FakeCapture(running=True)
    errors: list[str] = []
    activation = InputActivationUseCase(
        input_capture=keyboard,
        hotkey_capture=hotkey,
        is_active=lambda: False,
        set_active=lambda active: errors.append(f"state={active}"),
        notify_error=errors.append,
    )

    assert activation.enter_active() is True
    assert keyboard.running is True
    assert hotkey.running is False
    assert keyboard.started == 1
    assert hotkey.stopped == 1
    assert "boom" not in errors


def test_activation_rolls_back_to_hotkey_when_keyboard_start_fails():
    keyboard = FakeCapture(running=False, fail_start=True)
    hotkey = FakeCapture(running=True)
    states: list[bool] = []
    errors: list[str] = []
    activation = InputActivationUseCase(
        input_capture=keyboard,
        hotkey_capture=hotkey,
        is_active=lambda: False,
        set_active=states.append,
        notify_error=errors.append,
    )

    assert activation.enter_active() is False
    assert keyboard.running is False
    assert hotkey.running is True
    assert states == []
    assert errors == ["boom"]


def test_activation_enter_keeps_shared_tap_running_during_hotkey_to_keyboard_handoff():
    manager = FakeSharedTap()
    keyboard = SharedCapture(manager, running=False)
    hotkey = SharedCapture(manager, running=True)
    states: list[bool] = []
    activation = InputActivationUseCase(
        input_capture=keyboard,
        hotkey_capture=hotkey,
        is_active=lambda: False,
        set_active=states.append,
        notify_error=lambda message: None,
    )

    assert activation.enter_active() is True

    assert keyboard.running is True
    assert hotkey.running is False
    assert manager.starts == 1
    assert manager.stops == 0
    assert manager.active_registrations == 1
    assert states == [True]


def test_activation_exit_keeps_shared_tap_running_during_keyboard_to_hotkey_handoff():
    manager = FakeSharedTap()
    keyboard = SharedCapture(manager, running=True)
    hotkey = SharedCapture(manager, running=False)
    states: list[bool] = []
    activation = InputActivationUseCase(
        input_capture=keyboard,
        hotkey_capture=hotkey,
        is_active=lambda: True,
        set_active=states.append,
        notify_error=lambda message: None,
    )

    assert activation.exit_active() is True

    assert keyboard.running is False
    assert hotkey.running is True
    assert manager.starts == 1
    assert manager.stops == 0
    assert manager.active_registrations == 1
    assert states == [False]


def test_activation_enter_logs_handoff_progress(caplog):
    keyboard = FakeCapture(running=False)
    hotkey = FakeCapture(running=True)
    activation = InputActivationUseCase(
        input_capture=keyboard,
        hotkey_capture=hotkey,
        is_active=lambda: False,
        set_active=lambda active: None,
        notify_error=lambda message: None,
    )

    with caplog.at_level(logging.DEBUG):
        assert activation.enter_active() is True

    assert "InputActivation.enter_active begin" in caplog.text
    assert "hotkey_running=True" in caplog.text
    assert "InputActivation.enter_active input capture started" in caplog.text
    assert "InputActivation.enter_active input capture start returned" in caplog.text
    assert "InputActivation.enter_active stopping hotkey capture after handoff" in caplog.text


def test_activation_exit_logs_input_capture_stop_completion(caplog):
    keyboard = FakeCapture(running=True)
    hotkey = FakeCapture(running=False)
    activation = InputActivationUseCase(
        input_capture=keyboard,
        hotkey_capture=hotkey,
        is_active=lambda: True,
        set_active=lambda active: None,
        notify_error=lambda message: None,
    )

    with caplog.at_level(logging.DEBUG):
        assert activation.exit_active() is True

    assert "InputActivation.exit_active stopping input capture after handoff" in caplog.text
    assert "InputActivation.exit_active input capture stop returned" in caplog.text
