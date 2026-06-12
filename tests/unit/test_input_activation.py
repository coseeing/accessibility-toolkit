from application.input.activation import InputActivationUseCase


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
