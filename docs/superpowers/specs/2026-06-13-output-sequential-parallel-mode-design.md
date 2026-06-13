# Output Sequential/Parallel Mode Design

## Summary

This design adds a `Sequential` / `Parallel` output mode to `QueuedOutputService`. In sequential mode, consecutive `speak()` calls are guaranteed to execute in order through a shared scheduler. In parallel mode (default), each `speak()` call may interrupt previous speech. The design lays the foundation for future non-speech output types (tone, wave) by establishing a `shared_scheduler` that serializes cross-type output in sequential mode, while parallel mode allows each type's dedicated scheduler to run independently.

## Background

The current output chain is:

```
QueuedOutputService  ← controller-facing protocol adapter
  └─ SpeechService   ← backend switching, voice settings
       └─ pyttsx3 / nvda_controller  ← uses OutputScheduler for intra-sequence chunk ordering
```

`pyttsx3` and `nvda_controller` each hold their own reference to an `OutputScheduler` that serializes individual chunks within a speech sequence (text → break → text). There is currently no mechanism to enforce ordering between separate `speak()` calls.

A `shared_scheduler` — distinct from the backends' chunk-level schedulers — provides inter-sequence serialization without interfering with intra-sequence ordering.

## Goals

- Add `OutputMode.SEQUENTIAL` and `OutputMode.PARALLEL` to `QueuedOutputService`
- Sequential mode guarantees that two consecutive `speak()` calls execute in FIFO order
- Parallel mode preserves current behavior (backward compatible default)
- `cancel()` clears both the shared and speech schedulers
- `shutdown()` shuts down both schedulers
- Establish the `shared_scheduler` pattern for future tone/wave output types

## Non-Goals

- No new output types (tone, wave) are added in this round
- No changes to `SpeechService`, `pyttsx3`, or `nvda_controller`
- No changes to app-level `build_runtime()` or controller code
- No mode integration with the UI (mode is set programmatically)

## Architecture

```
PARALLEL mode (default):              SEQUENTIAL mode:
                                       
speak("a") ──→ SpeechService          speak("a") ──→ shared_scheduler
                  │                                     │
                  ▼                                     ▼
              speech_scheduler              ┌─ speech_scheduler
              (chunk ordering)              │   (chunk ordering)
              
speak("b") ──→ SpeechService              │
                  │                         speak("b") ──→ shared_scheduler (queued)
                  ▼                                     │
              speech_scheduler                         ▼
              (a and b may overlap)        ┌─ speech_scheduler
                                          │   (runs after a completes)
```

### Why `schedule(wait_done=False)` on the shared scheduler works?

`pyttsx3.speak(seq)` is called synchronously inside the shared scheduler's worker thread. During this call, it atomically adds all chunk tasks to the speech scheduler's queue. Because the shared scheduler processes jobs one at a time, all chunks from `speak("a")` arrive before any from `speak("b")`, regardless of when the chunk-level speech scheduler executes them.

No `wait_done=True`, `notify_done()`, or completion callback is needed between the two schedulers. The ordering guarantee derives from the shared scheduler's single-threaded worker processing one top-level speak job at a time.

## API

### `OutputMode`

```python
from enum import Enum

class OutputMode(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
```

### `QueuedOutputService`

```python
class QueuedOutputService:
    def __init__(self, *, speech: SpeechService) -> None:
        self._speech = speech
        self._mode = OutputMode.PARALLEL
        self._shared_scheduler = OutputScheduler()

    def set_mode(self, mode: OutputMode) -> None: ...
    def get_mode(self) -> OutputMode: ...

    def speak(self, sequence: SpeechSequence) -> None:
        # SEQUENTIAL: schedule through shared_scheduler
        # PARALLEL:  delegate directly to SpeechService (current behavior)

    def cancel(self) -> None:
        # cancel shared_scheduler + SpeechService

    def shutdown(self) -> None:
        # cancel + SpeechService.shutdown() + shared_scheduler.shutdown()

    # All other methods (pause, voice settings, etc.) unchanged — pass-through to SpeechService
```

### Mode switch behavior

Switching mode while items are already queued does **not** retroactively change their routing. Items already enqueued in `shared_scheduler` will complete in order. New `speak()` calls after the switch follow the new mode.

## Changes

| File | Change |
|---|---|
| `src/application/output_service.py` | Add `OutputMode` enum. Add `_mode`, `_shared_scheduler` fields, `set_mode`/`get_mode`, conditional routing in `speak()`, updated `cancel()` and `shutdown()`. |
| `tests/unit/test_output_service.py` | Add tests for: default mode, `set_mode`/`get_mode`, sequential ordering guarantee, `cancel()` clears shared queue, `shutdown()` cleans up shared scheduler. |

## Edge Cases

| Case | Behavior |
|---|---|
| Default mode | `PARALLEL` — identical to current behavior |
| `cancel()` in SEQUENTIAL mode | Clears `shared_scheduler` queue AND calls `SpeechService.cancel()` |
| `set_mode(PARALLEL)` while shared queue is non-empty | Queued items still execute in order; new calls go direct |
| `shutdown()` | Cancels both schedulers, then shuts down speech, then shared |
| Only speech output, no tone/wave yet | `shared_scheduler` acts as an inter-speak-sequence serializer — no functional difference from intra-sequence ordering in practice, but establishes the extension point |
| PARALLEL mode with only speech | Since speech is the only output type, all `speak()` calls go through the same `speech_scheduler`, resulting in FIFO ordering. The "parallel" behavior (independent schedulers per type) becomes observable only when tone/wave are added. |

## Testing

- Existing 3 tests in `test_output_service.py` must pass unchanged (default PARALLEL mode)
- New tests:
  - `test_output_mode_enum` — `SEQUENTIAL` and `PARALLEL` values
  - `test_default_mode_is_parallel` — `get_mode()` returns `PARALLEL`
  - `test_set_and_get_mode` — round-trip both values
  - `test_sequential_orders_consecutive_speak_calls` — two `speak()` calls arrive at backend in FIFO order
  - `test_cancel_in_sequential_clears_shared_queue` — pending sequential speak never executes after cancel
  - `test_shutdown_stops_shared_scheduler` — `shared_scheduler` worker thread stops
