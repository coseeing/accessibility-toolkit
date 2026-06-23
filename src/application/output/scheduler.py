import logging
import queue
import threading
import time
from concurrent.futures import Future
from dataclasses import dataclass, field
from typing import Callable

_logger = logging.getLogger(__name__)


@dataclass(slots=True)
class EventCallbacks:
    on_index_reached: Callable[[int | None], None] = field(
        default=lambda index: None
    )
    on_done: Callable[[], None] = field(default=lambda: None)


class CancellationToken:
    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def wait(self, timeout: float | None = None) -> bool:
        return self._event.wait(timeout)


class ScheduledFuture(Future):
    def then(self, fn: Callable[[Future], object]) -> "ScheduledFuture":
        next_future = ScheduledFuture()

        def _on_done(future: Future) -> None:
            try:
                if future.cancelled():
                    next_future.cancel()
                    return

                result = fn(future)
                if isinstance(result, Future):

                    def _on_chained_done(chained: Future) -> None:
                        if next_future.done():
                            return
                        if chained.cancelled():
                            next_future.cancel()
                            return
                        exception = chained.exception()
                        if exception is not None:
                            next_future.set_exception(exception)
                            return
                        next_future.set_result(chained.result())

                    result.add_done_callback(_on_chained_done)
                    return

                next_future.set_result(result)
            except Exception as exc:
                next_future.set_exception(exc)

        self.add_done_callback(_on_done)
        return next_future


@dataclass(slots=True)
class _ScheduledJob:
    owner: object
    run: Callable[[], object]
    wait_done: bool
    future: ScheduledFuture
    token: CancellationToken | None = None
    timeout: float | None = None


class Scheduler:
    def __init__(self, callbacks: EventCallbacks | None = None):
        self._callbacks = callbacks or EventCallbacks()
        self._queue: queue.Queue[_ScheduledJob | None] = queue.Queue()
        self._stop = threading.Event()
        self._state_lock = threading.Lock()

        self._current_owner: object | None = None
        self._current_voice: object | None = None
        self._current_token: CancellationToken | None = None
        self._current_done_event: threading.Event | None = None
        self._current_future: ScheduledFuture | None = None

        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def schedule(
        self,
        owner: object,
        action: Callable[[], object],
        *,
        wait_done: bool = False,
        cancel_token: CancellationToken | None = None,
        timeout: float | None = None,
    ) -> ScheduledFuture:
        future = ScheduledFuture()
        _logger.debug(
            "Scheduler.schedule owner=%s wait_done=%s token=%s timeout=%s future_id=%s",
            type(owner).__name__,
            wait_done,
            cancel_token is not None,
            timeout,
            id(future),
        )
        self._queue.put(
            _ScheduledJob(owner, action, wait_done, future, cancel_token, timeout)
        )
        return future

    def schedule_break(
        self, owner: object, seconds: float, *, cancel_token: CancellationToken | None = None
    ) -> ScheduledFuture:
        token = cancel_token or CancellationToken()

        def _break() -> None:
            token.wait(seconds)

        return self.schedule(owner, _break, cancel_token=token)

    def cancel_current(self) -> None:
        with self._state_lock:
            token = self._current_token
            owner = self._current_owner
            done = self._current_done_event
            future = self._current_future

        _logger.debug(
            "Scheduler.cancel_current owner=%s token=%s done_event=%s future_id=%s",
            type(owner).__name__ if owner is not None else None,
            token is not None,
            done is not None,
            id(future) if future is not None else None,
        )

        if token is not None:
            token.cancel()

        if future is not None and not future.done():
            future.cancel()

        if owner is not None and hasattr(owner, "stop"):
            try:
                _logger.debug(
                    "Scheduler.cancel_current calling owner.stop owner=%s",
                    type(owner).__name__,
                )
                owner.stop()
            except Exception:
                _logger.debug(
                    "Scheduler.cancel_current owner.stop raised",
                    exc_info=True,
                )
                pass

        if done is not None:
            done.set()

    def cancel_all(self) -> None:
        _logger.debug("Scheduler.cancel_all begin")
        self.cancel_current()

        cancelled_jobs = 0
        try:
            while True:
                job = self._queue.get_nowait()
                if isinstance(job, _ScheduledJob):
                    job.future.cancel()
                    cancelled_jobs += 1
                self._queue.task_done()
        except queue.Empty:
            pass
        _logger.debug("Scheduler.cancel_all completed cancelled_jobs=%d", cancelled_jobs)

    def shutdown(self) -> None:
        self.cancel_all()
        self._stop.set()
        self._queue.put(None)
        self._thread.join()

    def notify_index_reached(self, index: int | None) -> None:
        self._callbacks.on_index_reached(index)

    def notify_done(self) -> None:
        self._callbacks.on_done()
        with self._state_lock:
            done = self._current_done_event
        if done is not None:
            done.set()

    # Compatibility aliases for existing task-oriented callers/tests.
    add_task = schedule
    add_break_task = schedule_break

    def add_speak_task(
        self,
        owner: object,
        speak_fn: Callable[[], object],
        *,
        token: CancellationToken | None = None,
        timeout: float | None = None,
    ) -> ScheduledFuture:
        return self.schedule(
            owner,
            speak_fn,
            wait_done=True,
            cancel_token=token,
            timeout=timeout,
        )

    def notify_done_speaking(self) -> None:
        self.notify_done()

    def _worker(self) -> None:
        while not self._stop.is_set():
            job = self._queue.get()
            if job is None:
                return
            try:
                self._run_one(job)
            finally:
                self._queue.task_done()

    @staticmethod
    def _try_set_result(future: ScheduledFuture, result: object) -> None:
        if future.done():
            return
        future.set_result(result)

    @staticmethod
    def _try_set_exception(future: ScheduledFuture, exc: Exception) -> None:
        if future.done():
            return
        future.set_exception(exc)

    def _run_one(self, job: _ScheduledJob) -> None:
        _logger.debug(
            "Scheduler._run_one begin owner=%s wait_done=%s future_id=%s",
            type(job.owner).__name__,
            job.wait_done,
            id(job.future),
        )
        if job.future.cancelled():
            _logger.debug(
                "Scheduler._run_one skipped because future already cancelled future_id=%s",
                id(job.future),
            )
            return

        if job.token is not None and job.token.is_cancelled():
            job.future.cancel()
            _logger.debug(
                "Scheduler._run_one cancelled before start via token future_id=%s",
                id(job.future),
            )
            return

        with self._state_lock:
            self._current_owner = job.owner
            self._current_voice = job.owner
            self._current_token = job.token
            self._current_future = job.future

        try:
            if not job.wait_done:
                result = job.run()
                if job.token is not None and job.token.is_cancelled():
                    if not job.future.done():
                        job.future.cancel()
                    _logger.debug(
                        "Scheduler._run_one cancelled after run via token future_id=%s",
                        id(job.future),
                    )
                    return
                self._try_set_result(job.future, result)
                _logger.debug(
                    "Scheduler._run_one completed without wait_done future_id=%s",
                    id(job.future),
                )
                return

            done = threading.Event()
            with self._state_lock:
                self._current_done_event = done

            job.run()
            _logger.debug(
                "Scheduler._run_one owner.run returned wait_done=%s future_id=%s",
                job.wait_done,
                id(job.future),
            )
            start = time.monotonic()

            while True:
                if self._stop.is_set():
                    job.future.cancel()
                    return

                if job.token is not None and job.token.is_cancelled():
                    if not job.future.done():
                        job.future.cancel()
                    _logger.debug(
                        "Scheduler._run_one cancelled while waiting via token future_id=%s",
                        id(job.future),
                    )
                    return

                if done.wait(timeout=0.01):
                    self._try_set_result(job.future, None)
                    _logger.debug(
                        "Scheduler._run_one observed done event future_id=%s",
                        id(job.future),
                    )
                    return

                if job.timeout is not None and time.monotonic() - start >= job.timeout:
                    self._try_set_exception(job.future, TimeoutError("Speech timeout"))
                    if done.wait(timeout=0.1):
                        self._try_set_result(job.future, None)
                    return
        except Exception as exc:
            self._try_set_exception(job.future, exc)
            _logger.debug(
                "Scheduler._run_one raised exception future_id=%s",
                id(job.future),
                exc_info=True,
            )
        finally:
            with self._state_lock:
                self._current_owner = None
                self._current_voice = None
                self._current_token = None
                self._current_done_event = None
                self._current_future = None
            _logger.debug(
                "Scheduler._run_one end future_id=%s",
                id(job.future),
            )
