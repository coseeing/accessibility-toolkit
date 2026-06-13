# Output Sequential/Parallel Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `OutputMode` (SEQUENTIAL / PARALLEL) to `QueuedOutputService` with a `shared_scheduler` that serializes consecutive `speak()` calls in sequential mode.

**Architecture:** A `shared_scheduler` (separate from the backend's chunk-level scheduler) serializes top-level `speak()` calls. PARALLEL mode (default) delegates directly to `SpeechService` (backward compatible). SEQUENTIAL mode routes through `shared_scheduler` which calls `speech.speak()` inside its worker thread, guaranteeing FIFO order because `pyttsx3.speak()` atomically adds all chunks.

**Tech Stack:** Python 3, `OutputScheduler`, `Enum`

---

### File Structure

| File | Responsibility |
|---|---|
| `src/application/output_service.py` | `OutputMode` enum + `QueuedOutputService` with mode routing, cancel, shutdown |
| `tests/unit/test_output_service.py` | Tests for mode API, sequential ordering, cancel, shutdown |

`build_service()` in the test file already creates a real `OutputScheduler`, real `SpeechService`, and real `QueuedOutputService` backed by `FakeSpeechOutput`. New tests reuse this helper.

---

### Task 1: Add new tests to `test_output_service.py`

**Files:**
- Modify: `tests/unit/test_output_service.py`

- [ ] **Step 1: Add imports and new test functions**

Append the following to `tests/unit/test_output_service.py`:

```python
import threading

from application.output_service import OutputMode


def test_output_mode_enum_values() -> None:
    assert OutputMode.SEQUENTIAL.value == "sequential"
    assert OutputMode.PARALLEL.value == "parallel"


def test_default_mode_is_parallel() -> None:
    service, _created, _scheduler = build_service()
    assert service.get_mode() == OutputMode.PARALLEL


def test_set_and_get_mode() -> None:
    service, _created, _scheduler = build_service()

    service.set_mode(OutputMode.SEQUENTIAL)
    assert service.get_mode() == OutputMode.SEQUENTIAL

    service.set_mode(OutputMode.PARALLEL)
    assert service.get_mode() == OutputMode.PARALLEL


def test_sequential_orders_consecutive_speak_calls() -> None:
    service, created, _scheduler = build_service()
    service.set_mode(OutputMode.SEQUENTIAL)

    seq_a = SpeechSequence(items=("a",))
    seq_b = SpeechSequence(items=("b",))
    service.speak(seq_a)
    service.speak(seq_b)

    sentinel = service._shared_scheduler.schedule(service, lambda: None)
    sentinel.result(timeout=2)

    assert created[0].spoken == [seq_a, seq_b]


def test_cancel_in_sequential_clears_shared_queue() -> None:
    service, created, _scheduler = build_service()
    service.set_mode(OutputMode.SEQUENTIAL)

    seq_a = SpeechSequence(items=("a",))
    seq_b = SpeechSequence(items=("b",))

    service.speak(seq_a)
    sentinel = service._shared_scheduler.schedule(service, lambda: None)
    sentinel.result(timeout=2)

    service.speak(seq_b)
    service.cancel()

    sentinel2 = service._shared_scheduler.schedule(service, lambda: None)
    sentinel2.result(timeout=2)

    assert created[0].spoken == [seq_a]


def test_shutdown_stops_shared_scheduler() -> None:
    service, _created, _scheduler = build_service()
    service.set_mode(OutputMode.SEQUENTIAL)

    seq = SpeechSequence(items=("x",))
    service.speak(seq)
    sentinel = service._shared_scheduler.schedule(service, lambda: None)
    sentinel.result(timeout=2)

    service.shutdown()

    assert not service._shared_scheduler._thread.is_alive()


def test_parallel_mode_is_backward_compatible() -> None:
    service, created, _scheduler = build_service()

    speech = SpeechSequence(items=("hello",))
    service.speak(speech)
    service.pause(True)
    service.cancel()

    assert created[0].spoken == [speech]
    assert created[0].paused == [True]
    assert created[0].cancelled == 1
    service.shutdown()
```

- [ ] **Step 2: Run new tests, verify they fail**

```bash
python3 -m pytest tests/unit/test_output_service.py -k "test_output_mode_enum or test_default_mode_is_parallel or test_set_and_get_mode or test_sequential_orders_consecutive_speak_calls or test_cancel_in_sequential_clears_shared_queue or test_shutdown_stops_shared_scheduler or test_parallel_mode_is_backward_compatible" -v
```

Expected: all new tests FAIL (`OutputMode` not defined, `set_mode` not defined, `_shared_scheduler` not found, etc.).

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_output_service.py
git commit -m "test: add output mode sequential/parallel tests"
```

---

### Task 2: Implement `OutputMode` enum and mode API

**Files:**
- Modify: `src/application/output_service.py`

- [ ] **Step 1: Add `OutputMode` enum and mode infrastructure**

Replace the current `src/application/output_service.py` with:

```python
from enum import Enum
from typing import Protocol, runtime_checkable

from application.output_scheduler import OutputScheduler
from application.speech_service import SpeechService
from interop.speech.speech_sequence import SpeechSequence


class OutputMode(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


@runtime_checkable
class SpeechOutputService(Protocol):
    def speak(self, sequence: SpeechSequence) -> None: ...
    def cancel(self) -> None: ...
    def pause(self, is_paused: bool) -> None: ...
    def get_backend_options(self) -> tuple[tuple[str, str], ...]: ...
    def get_selected_backend(self) -> str: ...
    def set_backend(self, backend_id: str) -> None: ...
    def list_voices(self) -> tuple[tuple[str, str], ...]: ...
    def get_voice(self) -> str | None: ...
    def set_voice(self, voice_id: str) -> None: ...
    def get_rate(self) -> int | None: ...
    def set_rate(self, value: int) -> None: ...
    def get_pitch(self) -> int | None: ...
    def set_pitch(self, value: int) -> None: ...
    def get_volume(self) -> int | None: ...
    def set_volume(self, value: int) -> None: ...
    def shutdown(self) -> None: ...


class QueuedOutputService:
    def __init__(self, *, speech: SpeechService) -> None:
        self._speech = speech
        self._mode = OutputMode.PARALLEL
        self._shared_scheduler = OutputScheduler()

    def set_mode(self, mode: OutputMode) -> None:
        self._mode = mode

    def get_mode(self) -> OutputMode:
        return self._mode

    def speak(self, sequence: SpeechSequence) -> None:
        if self._mode == OutputMode.SEQUENTIAL:
            self._shared_scheduler.schedule(self, lambda: self._speech.speak(sequence))
        else:
            self._speech.speak(sequence)

    def cancel(self) -> None:
        self._shared_scheduler.cancel_all()
        self._speech.cancel()

    def pause(self, is_paused: bool) -> None:
        self._speech.pause(is_paused)

    def get_backend_options(self) -> tuple[tuple[str, str], ...]:
        return self._speech.get_backend_options()

    def get_selected_backend(self) -> str:
        return self._speech.get_selected_backend()

    def set_backend(self, backend_id: str) -> None:
        self._speech.set_backend(backend_id)

    def list_voices(self) -> tuple[tuple[str, str], ...]:
        return self._speech.list_voices()

    def get_voice(self) -> str | None:
        return self._speech.get_voice()

    def set_voice(self, voice_id: str) -> None:
        self._speech.set_voice(voice_id)

    def get_rate(self) -> int | None:
        return self._speech.get_rate()

    def set_rate(self, value: int) -> None:
        self._speech.set_rate(value)

    def get_pitch(self) -> int | None:
        return self._speech.get_pitch()

    def set_pitch(self, value: int) -> None:
        self._speech.set_pitch(value)

    def get_volume(self) -> int | None:
        return self._speech.get_volume()

    def set_volume(self, value: int) -> None:
        self._speech.set_volume(value)

    def shutdown(self) -> None:
        self.cancel()
        self._speech.shutdown()
        self._shared_scheduler.shutdown()
```

- [ ] **Step 2: Run new tests, verify they pass**

```bash
python3 -m pytest tests/unit/test_output_service.py -k "test_output_mode_enum or test_default_mode_is_parallel or test_set_and_get_mode or test_sequential_orders_consecutive_speak_calls or test_cancel_in_sequential_clears_shared_queue or test_shutdown_stops_shared_scheduler or test_parallel_mode_is_backward_compatible" -v
```

Expected: all 7 new tests PASS.

- [ ] **Step 3: Run existing tests, verify backward compatibility**

```bash
python3 -m pytest tests/unit/test_output_service.py tests/unit/test_key_echo_app_service.py tests/unit/test_app_wx.py -v
```

Expected: ALL existing tests still PASS (default PARALLEL mode behaves identically).

- [ ] **Step 4: Commit**

```bash
git add src/application/output_service.py
git commit -m "feat: add OutputMode SEQUENTIAL/PARALLEL to QueuedOutputService"
```

---

### Task 3: Run full test suite

- [ ] **Step 1: Run full suite**

```bash
python3 -m pytest tests/unit/ tests/integration/ -v
```

Expected: 335+ tests pass (all existing + new).

- [ ] **Step 2: Commit any remaining changes if needed**

```bash
git status
```
