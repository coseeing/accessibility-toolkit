import queue
import threading
import time
from concurrent.futures import Future
from dataclasses import dataclass
from typing import Callable

from adapters.worldvoice_task.events import SpeechEventCallbacks


class CancellationToken:
    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def wait(self, timeout: float | None = None) -> bool:
        return self._event.wait(timeout)


class SpeechFuture(Future):
    def then(self, fn: Callable[[Future], object]) -> "SpeechFuture":
        next_future = SpeechFuture()

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
class _Task:
    voice_instance: object
    run: Callable[[], object]
    wait_done: bool
    future: SpeechFuture
    token: CancellationToken | None = None
    timeout: float | None = None


class TaskManager:
    def __init__(self, callbacks: SpeechEventCallbacks | None = None):
        self._callbacks = callbacks or SpeechEventCallbacks()
        self._queue: queue.Queue[_Task | None] = queue.Queue()
        self._stop = threading.Event()
        self._state_lock = threading.Lock()

        self._current_voice: object | None = None
        self._current_token: CancellationToken | None = None
        self._current_done_event: threading.Event | None = None
        self._current_future: SpeechFuture | None = None

        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def add_task(
        self,
        voice_instance: object,
        fn: Callable[[], object],
        *,
        token: CancellationToken | None = None,
    ) -> SpeechFuture:
        future = SpeechFuture()
        self._queue.put(_Task(voice_instance, fn, False, future, token))
        return future

    def add_break_task(self, voice_instance: object, seconds: float) -> SpeechFuture:
        token = CancellationToken()

        def _break() -> None:
            token.wait(seconds)

        return self.add_task(voice_instance, _break, token=token)

    def add_speak_task(
        self,
        voice_instance: object,
        speak_fn: Callable[[], object],
        *,
        token: CancellationToken | None = None,
        timeout: float | None = None,
    ) -> SpeechFuture:
        future = SpeechFuture()
        self._queue.put(_Task(voice_instance, speak_fn, True, future, token, timeout))
        return future

    def cancel_current(self) -> None:
        with self._state_lock:
            token = self._current_token
            voice = self._current_voice
            done = self._current_done_event
            future = self._current_future

        if token is not None:
            token.cancel()

        if future is not None and not future.done():
            future.cancel()

        if voice is not None and hasattr(voice, "stop"):
            try:
                voice.stop()
            except Exception:
                pass

        if done is not None:
            done.set()

    def cancel(self) -> None:
        self.cancel_current()

        try:
            while True:
                task = self._queue.get_nowait()
                if isinstance(task, _Task):
                    task.future.cancel()
                self._queue.task_done()
        except queue.Empty:
            pass

    def shutdown(self) -> None:
        self.cancel()
        self._stop.set()
        self._queue.put(None)
        self._thread.join()

    def notify_index_reached(self, index: int | None) -> None:
        self._callbacks.on_index_reached(index)

    def notify_done_speaking(self) -> None:
        self._callbacks.on_done_speaking()
        with self._state_lock:
            done = self._current_done_event
        if done is not None:
            done.set()

    def _worker(self) -> None:
        while not self._stop.is_set():
            task = self._queue.get()
            if task is None:
                return
            try:
                self._run_one(task)
            finally:
                self._queue.task_done()

    @staticmethod
    def _try_set_result(future: SpeechFuture, result: object) -> None:
        if future.done():
            return
        future.set_result(result)

    @staticmethod
    def _try_set_exception(future: SpeechFuture, exc: Exception) -> None:
        if future.done():
            return
        future.set_exception(exc)

    def _run_one(self, task: _Task) -> None:
        if task.future.cancelled():
            return

        if task.token is not None and task.token.is_cancelled():
            task.future.cancel()
            return

        with self._state_lock:
            self._current_voice = task.voice_instance
            self._current_token = task.token
            self._current_future = task.future

        try:
            if not task.wait_done:
                result = task.run()
                if task.token is not None and task.token.is_cancelled():
                    if not task.future.done():
                        task.future.cancel()
                    return
                self._try_set_result(task.future, result)
                return

            done = threading.Event()
            with self._state_lock:
                self._current_done_event = done

            task.run()
            start = time.monotonic()

            while True:
                if self._stop.is_set():
                    task.future.cancel()
                    return

                if task.token is not None and task.token.is_cancelled():
                    task.future.cancel()
                    return

                if task.timeout is not None and time.monotonic() - start > task.timeout:
                    self._try_set_exception(task.future, TimeoutError("Speech timeout"))
                    return

                if done.wait(0.05):
                    self._try_set_result(task.future, True)
                    return
        except Exception as exc:
            self._try_set_exception(task.future, exc)
        finally:
            with self._state_lock:
                self._current_voice = None
                self._current_token = None
                self._current_done_event = None
                self._current_future = None
