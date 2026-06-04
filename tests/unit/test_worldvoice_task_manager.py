import time

from adapters.worldvoice_task.events import SpeechEventCallbacks
from adapters.worldvoice_task.task_manager import TaskManager


class FakeVoice:
    def __init__(self):
        self.stop_count = 0

    def stop(self):
        self.stop_count += 1


def test_task_manager_completes_basic_task():
    manager = TaskManager()
    voice = FakeVoice()
    called = []

    future = manager.add_task(voice, lambda: called.append("ran"))

    assert future.result(timeout=0.5) is None
    assert called == ["ran"]
    manager.shutdown()


def test_task_manager_break_task_waits_and_can_cancel():
    manager = TaskManager()
    voice = FakeVoice()
    future = manager.add_break_task(voice, 0.2)

    deadline = time.monotonic() + 0.5
    while manager._current_voice is None and time.monotonic() < deadline:
        time.sleep(0.01)

    manager.cancel_current()

    assert voice.stop_count == 1
    future.cancel()
    manager.shutdown()


def test_task_manager_notifies_done_speaking_callback():
    called = []
    manager = TaskManager(
        callbacks=SpeechEventCallbacks(on_done_speaking=lambda: called.append("done"))
    )

    manager.notify_done_speaking()

    assert called == ["done"]
    manager.shutdown()
