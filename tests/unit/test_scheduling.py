import threading
import time
from concurrent.futures import CancelledError

import pytest

from accessibility_toolkit.scheduling import (
    CancellationToken,
    EventCallbacks,
    ScheduledFuture,
    Scheduler,
)


class FakeOwner:
    def __init__(self):
        self.stop_count = 0

    def stop(self):
        self.stop_count += 1


def wait_for(predicate, *, timeout: float = 0.5) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("timed out waiting for condition")


def test_output_scheduler_completes_basic_task():
    scheduler = Scheduler()
    owner = FakeOwner()
    called = []

    future = scheduler.schedule(owner, lambda: called.append("ran"))

    assert future.result(timeout=0.5) is None
    assert called == ["ran"]
    scheduler.shutdown()


def test_output_scheduler_break_task_waits_and_can_cancel():
    scheduler = Scheduler()
    owner = FakeOwner()
    future = scheduler.schedule_break(owner, 0.2)

    deadline = time.monotonic() + 0.5
    while scheduler._current_owner is None and time.monotonic() < deadline:
        time.sleep(0.01)

    scheduler.cancel_current()

    assert owner.stop_count == 1
    with pytest.raises(CancelledError):
        future.result(timeout=0.5)
    scheduler.shutdown()


def test_output_scheduler_notifies_done_callback():
    called = []
    scheduler = Scheduler(callbacks=EventCallbacks(on_done=lambda: called.append("done")))

    scheduler.notify_done()

    assert called == ["done"]
    scheduler.shutdown()


def test_output_future_then_cancels_when_chained_future_is_cancelled():
    first = ScheduledFuture()
    chained = ScheduledFuture()
    next_future = first.then(lambda _: chained)

    first.set_result(None)
    chained.cancel()

    assert next_future.cancelled() is True


def test_output_scheduler_serializes_tasks() -> None:
    scheduler = Scheduler()
    owner = FakeOwner()
    events: list[str] = []

    scheduler.schedule(owner, lambda: events.append("first"))
    scheduler.schedule(owner, lambda: events.append("second"))

    wait_for(lambda: events == ["first", "second"])
    scheduler.shutdown()


def test_output_scheduler_cancel_all_skips_pending_tasks() -> None:
    scheduler = Scheduler()
    owner = FakeOwner()
    entered = threading.Event()
    release = threading.Event()
    events: list[str] = []

    def first() -> None:
        events.append("first")
        entered.set()
        release.wait(timeout=0.5)

    scheduler.schedule(owner, first)
    entered.wait(timeout=0.5)
    scheduler.schedule(owner, lambda: events.append("second"))

    scheduler.cancel_all()
    release.set()
    wait_for(lambda: owner.stop_count == 1)

    assert events == ["first"]
    scheduler.shutdown()


def test_cancellation_token_can_cancel_scheduled_tasks() -> None:
    scheduler = Scheduler()
    owner = FakeOwner()
    token = CancellationToken()
    token.cancel()

    future = scheduler.schedule(owner, lambda: None, cancel_token=token)

    with pytest.raises(CancelledError):
        future.result(timeout=0.5)
    scheduler.shutdown()
