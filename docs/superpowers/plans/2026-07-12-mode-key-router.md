# Multi-Key Mode Router Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the mode-owned router already committed in `255c482` with order-independent multi-key chords, unified prefix buffering, binding ownership, and a default long-press scheduler.

**Architecture:** `KeyEventRouter` remains the only mode input router. It keeps raw captured events for fallback replay, maintains normalized matching state separately, and resolves exact chords, longer-prefix candidates, key-up ownership, and long-press timers through one deterministic state machine. Platform capture and NVDA Remote payload conversion continue to receive unmodified `CapturedKeyEvent` values.

**Tech Stack:** Python 3.14, dataclasses, `threading.Timer`, pytest, USB HID keyboard usages, wxPython-compatible injected scheduler protocol.

## Global Constraints

- Start from commit `255c482 feat: add mode key event router`; do not recreate the already-landed ModeManager/app migration.
- `KeyChord.usages` contains one or more non-modifier HID usages; `KeyChord.modifiers` contains normalized Ctrl, Shift, Alt, and Meta values.
- Chord matching is order-independent and requires exact general-key and modifier sets.
- Bindings remain immutable after `KeyEventRouter` construction.
- Prefix buffering applies equally to general keys and modifiers and immediately returns `HANDLED_STOP`.
- Matching normalization must never mutate `KeyEvent`, `CapturedKeyEvent`, `native_context`, or NVDA Remote payloads.
- Handler exceptions are never caught by the router. Synchronous exceptions propagate to the app service; asynchronous exceptions remain in the scheduler execution context.
- Protect all mutable router state and timer callbacks with one `threading.RLock`; handlers may re-enter router lifecycle on the same thread.
- Missing ignored fixture `Access8Graph/tests/test.graphml` and its 14 baseline failures remain out of scope.

---

### Task 1: Provide the default delayed scheduler

**Files:**
- Modify: `src/accessibility_toolkit/input/router.py`
- Test: `tests/unit/test_key_router.py`

**Interfaces:**
- Consumes: `DelayedScheduler.schedule(delay_seconds: float, callback: Callable[[], None]) -> ScheduledCall`.
- Produces: `KeyEventRouter(..., delayed_scheduler: DelayedScheduler | None = None)` that uses an internal `threading.Timer` scheduler when omitted.

- [ ] **Step 1: Write failing tests for default and injected scheduling**

Add a timer factory seam to the expected API and test it without sleeping:

```python
def test_long_press_uses_default_scheduler_when_none_is_injected(monkeypatch):
    created = []

    class FakeTimer:
        def __init__(self, seconds, callback):
            self.seconds = seconds
            self.callback = callback
            self.daemon = False
            self.started = False
            self.cancelled = False
            created.append(self)

        def start(self):
            self.started = True

        def cancel(self):
            self.cancelled = True

    monkeypatch.setattr("accessibility_toolkit.input.router.threading.Timer", FakeTimer)
    router = KeyEventRouter(
        bindings=(
            KeyBinding(
                chord=KeyChord(HID.A),
                trigger=KeyTrigger.LONG_PRESS,
                duration_seconds=1.25,
                handler=lambda _event: AppKeyEventResult.HANDLED_STOP,
            ),
        )
    )

    assert router.handle(key(HID.A)) is AppKeyEventResult.HANDLED_STOP
    assert created[0].seconds == 1.25
    assert created[0].daemon is True
    assert created[0].started is True
```

Keep the existing fake `DelayedScheduler` test and assert an injected scheduler is used instead of `threading.Timer`.
Add a test whose long-press handler calls `router.reset()` to prove the reentrant lock does not deadlock and the pending state is cleared.

- [ ] **Step 2: Run the scheduler tests and verify RED**

Run: `pytest tests/unit/test_key_router.py -q`

Expected: FAIL because long-press bindings currently reject a missing `delayed_scheduler`.

- [ ] **Step 3: Implement the default scheduler adapter**

Add these private types in `router.py`:

```python
import threading

class _ThreadingDelayedScheduler:
    def schedule(
        self, delay_seconds: float, callback: Callable[[], None]
    ) -> ScheduledCall:
        timer = threading.Timer(delay_seconds, callback)
        timer.daemon = True
        timer.start()
        return timer
```

Set `self._delayed_scheduler = delayed_scheduler or _ThreadingDelayedScheduler()` and
`self._state_lock = threading.RLock()`. Remove the constructor error that requires injection. Wrap `handle()`,
`reset()`, and the timer callback's state verification/mutation in this same lock. Invoke the long-press handler
while holding the reentrant lock so `reset()` cannot race past a callback that has already claimed the pending
press; allow same-thread lifecycle re-entry. Do not catch callback exceptions.

- [ ] **Step 4: Run the focused scheduler tests and verify GREEN**

Run: `pytest tests/unit/test_key_router.py -q`

Expected: the default/injected scheduler tests pass; multi-key tests added in later tasks are not present yet.

- [ ] **Step 5: Commit the scheduler behavior**

```bash
git add src/accessibility_toolkit/input/router.py tests/unit/test_key_router.py
git commit -m "feat: add default long press scheduler"
```

### Task 2: Change KeyChord to an exact multi-key value object

**Files:**
- Modify: `src/accessibility_toolkit/input/router.py`
- Modify: `src/apps/access8graph/service.py`
- Modify: `src/apps/key_echo/service.py`
- Modify: `src/apps/nvda_remote/service.py`
- Modify: `tests/unit/test_key_router.py`
- Test: `tests/unit/test_access8graph_app_service.py`
- Test: `tests/unit/test_key_echo_app_service.py`
- Test: `tests/unit/test_nvda_remote_app_service.py`

**Interfaces:**
- Produces: `KeyChord(usages: frozenset[int], modifiers: frozenset[Modifier] = frozenset())`.
- Preserves: matched handlers receive the `KeyEvent` that completed/released the chord; fallback receives the original `KeyEvent | CapturedKeyEvent`.

- [ ] **Step 1: Write failing value-object and exact-match tests**

Add `import pytest` and this test helper before the new cases:

```python
def binding(
    usages: set[int],
    trigger: KeyTrigger,
    handler,
    *,
    modifiers: set[Modifier] | None = None,
    duration_seconds: float | None = None,
) -> KeyBinding:
    return KeyBinding(
        chord=KeyChord(
            usages=frozenset(usages),
            modifiers=frozenset(modifiers or ()),
        ),
        trigger=trigger,
        handler=lambda event: handler(event)
        or AppKeyEventResult.HANDLED_STOP,
        duration_seconds=duration_seconds,
    )


def handled(_event) -> AppKeyEventResult:
    return AppKeyEventResult.HANDLED_STOP
```

```python
def test_key_chord_requires_at_least_one_general_key():
    with pytest.raises(ValueError, match="at least one usage"):
        KeyChord(usages=frozenset())


def test_multi_key_chord_is_order_independent_and_exact():
    calls = []
    router = KeyEventRouter(
        bindings=(
            KeyBinding(
                chord=KeyChord(usages=frozenset({HID.A, HID.B})),
                trigger=KeyTrigger.KEY_DOWN,
                handler=lambda event: calls.append(event.usage)
                or AppKeyEventResult.HANDLED_STOP,
            ),
        )
    )

    assert router.handle(key(HID.B)) is AppKeyEventResult.UNHANDLED
    assert router.handle(key(HID.A)) is AppKeyEventResult.HANDLED_STOP
    assert calls == [HID.A]
    assert router.handle(key(HID.C)) is AppKeyEventResult.UNHANDLED
    assert calls == [HID.A]
```

Add the reverse A-then-B order and `Ctrl+A+B` tests. Assert left/right Ctrl both match `Modifier.CONTROL`, while the fallback receives the unchanged physical modifier usage and unchanged `CapturedKeyEvent.native_context` when the chord does not form.

- [ ] **Step 2: Run the value-object tests and verify RED**

Run: `pytest tests/unit/test_key_router.py -q`

Expected: FAIL because `KeyChord` currently has singular `usage` and the router tracks only modifiers.

- [ ] **Step 3: Implement the new KeyChord contract and pressed-key state**

Replace `KeyChord` and add validation:

```python
@dataclass(frozen=True, slots=True)
class KeyChord:
    usages: frozenset[int]
    modifiers: frozenset[Modifier] = frozenset()

    def __post_init__(self) -> None:
        if not self.usages:
            raise ValueError("KeyChord requires at least one usage")
        if any(usage in _MODIFIER_BY_USAGE for usage in self.usages):
            raise ValueError("KeyChord usages cannot contain modifier usages")
```

Track `_pressed_usages: set[int]` separately from `_pressed_modifier_usages`. Because a modifier-only prefix such as
Ctrl down must be representable while public `KeyChord` forbids empty `usages`, add this private state value:

```python
@dataclass(frozen=True, slots=True)
class _MatchState:
    usages: frozenset[int]
    modifiers: frozenset[Modifier]


def _current_state(self) -> _MatchState:
    return _MatchState(
        usages=frozenset(self._pressed_usages),
        modifiers=self._active_modifiers(),
    )
```

Preserve the original input object before updating matching state. Never replace its HID usage.

- [ ] **Step 4: Migrate every existing single-key binding**

Change all app construction sites from:

```python
KeyChord(HID.ESCAPE)
```

to:

```python
KeyChord(usages=frozenset({HID.ESCAPE}))
```

Apply the same migration to Access8Graph command bindings and all router tests. Do not change app command maps, fallback handlers, or ModeManager lifecycle.

- [ ] **Step 5: Run router and app compatibility tests**

Run:

`pytest tests/unit/test_key_router.py tests/unit/test_mode_manager.py tests/unit/test_key_echo_app_service.py tests/unit/test_nvda_remote_app_service.py tests/unit/test_access8graph_input.py tests/unit/test_access8graph_use_cases.py -q`

Expected: PASS.

- [ ] **Step 6: Commit the multi-key value model**

```bash
git add src/accessibility_toolkit/input/router.py src/apps/access8graph/service.py src/apps/key_echo/service.py src/apps/nvda_remote/service.py tests/unit/test_key_router.py tests/unit/test_mode_manager.py
git commit -m "feat: support multi-key chord values"
```

### Task 3: Implement unified prefix buffering and fallback replay

**Files:**
- Modify: `src/accessibility_toolkit/input/router.py`
- Modify: `tests/unit/test_key_router.py`

**Interfaces:**
- Consumes: immutable indexed `KeyBinding` values and raw `KeyEventInput` events.
- Produces: deterministic prefix buffering for general keys and modifiers, exact-chord dispatch, and original-event fallback replay.

- [ ] **Step 1: Write failing prefix tests for general keys**

```python
def test_shorter_binding_waits_for_longer_chord():
    calls = []
    router = KeyEventRouter(
        bindings=(
            binding({HID.A}, KeyTrigger.KEY_DOWN, lambda _e: calls.append("a")),
            binding({HID.A, HID.B}, KeyTrigger.KEY_DOWN, lambda _e: calls.append("ab")),
            binding({HID.A, HID.B, HID.C}, KeyTrigger.KEY_DOWN, lambda _e: calls.append("abc")),
        )
    )

    assert router.handle(key(HID.A)) is AppKeyEventResult.HANDLED_STOP
    assert router.handle(key(HID.B)) is AppKeyEventResult.HANDLED_STOP
    assert calls == []
    assert router.handle(key(HID.B, pressed=False)) is AppKeyEventResult.HANDLED_STOP
    assert calls == ["ab"]
```

Add a second test where C completes `A+B+C` and neither shorter handler runs.

- [ ] **Step 2: Write failing replay tests for general and modifier prefixes**

```python
def test_failed_modifier_prefix_replays_original_events_to_fallback():
    native = object()
    replayed = []
    router = KeyEventRouter(
        bindings=(binding({HID.A}, KeyTrigger.KEY_DOWN, handled,
                          modifiers={Modifier.CONTROL}),),
        fallback=lambda event: replayed.append(event)
        or AppKeyEventResult.HANDLED_STOP,
    )
    down = CapturedKeyEvent(key(HID.LEFT_CONTROL), native_context=native)
    up = CapturedKeyEvent(key(HID.LEFT_CONTROL, False), native_context=native)

    assert router.handle(down) is AppKeyEventResult.HANDLED_STOP
    assert replayed == []
    assert router.handle(up) is AppKeyEventResult.HANDLED_STOP
    assert replayed == [down, up]
```

Add the same replay assertion for an unbound A prefix of `A+B`. Add a no-fallback case asserting buffered events are discarded and release remains `HANDLED_STOP`.

- [ ] **Step 3: Run the prefix tests and verify RED**

Run: `pytest tests/unit/test_key_router.py -q`

Expected: FAIL because events currently reach fallback immediately and no general-key prefix state exists.

- [ ] **Step 4: Add explicit buffered-state records and candidate indexing**

Add these private records:

```python
@dataclass(slots=True)
class _BufferedInput:
    original: KeyEventInput
    event: KeyEvent


@dataclass(slots=True)
class _DeferredChord:
    chord: KeyChord
    completion_event: KeyEvent
    key_down_binding: KeyBinding | None
```

Pre-index all unique binding chords. Define prefix matching exactly as:

```python
def _is_prefix(current: _MatchState, target: KeyChord) -> bool:
    return (
        current.usages <= target.usages
        and current.modifiers <= target.modifiers
        and (
            current.usages != target.usages
            or current.modifiers != target.modifiers
        )
    )
```

Maintain `_buffered_inputs` in arrival order and `_deferred_chord` as the most specific exact chord reached but delayed by a strict superset or long-press decision.

- [ ] **Step 5: Implement deterministic key-down precedence**

For a non-repeat key-down, update physical state, append the original input when the resulting state is an exact chord or prefix, then apply this precedence:

1. If current state exactly matches a long-press binding, schedule it and retain its key-down binding as the deferred short action.
2. If current state exactly matches a key-down binding and is a strict prefix of another registered chord, store it as `_deferred_chord` and return `HANDLED_STOP`.
3. If current state exactly matches a key-down binding with no strict supersets, call its handler. Return its result and clear buffered prefix state only after recording ownership in Task 4.
4. If current state is only a strict prefix, return `HANDLED_STOP` without fallback.
5. If current state matches neither exact nor prefix candidates, cancel pending long-press state, replay buffered inputs plus the current input to fallback in original order, clear prefix state, and return `HANDLED_STOP`. With no fallback, discard them and still return `HANDLED_STOP`.

Repeated key-down for an already-held physical usage must not append another buffered input, reset a long-press timer, or re-trigger a multi-key chord. Preserve existing repeat dispatch only for a non-deferred single-key key-down binding.

- [ ] **Step 6: Implement release resolution and verify GREEN**

Before removing a released physical key, inspect the complete pre-release chord:

- If `_deferred_chord.chord` equals the pre-release chord, cancel its long timer, execute its delayed key-down handler when present, ignore that delayed handler result, clear buffered state, remove the physical key, and return `HANDLED_STOP`.
- If no exact deferred chord formed, append the release input, replay the buffer to fallback in order, clear it, remove the physical key, and return `HANDLED_STOP`.
- If a chord was completed by a longer binding, clear obsolete shorter candidates so they can never fire later.

Run: `pytest tests/unit/test_key_router.py -q`

Expected: all prefix, replay, exact-match, and existing long-press tests pass.

- [ ] **Step 7: Commit prefix buffering**

```bash
git add src/accessibility_toolkit/input/router.py tests/unit/test_key_router.py
git commit -m "feat: buffer multi-key chord prefixes"
```

### Task 4: Add chord ownership, multi-key key-up, and long-press lifecycle

**Files:**
- Modify: `src/accessibility_toolkit/input/router.py`
- Modify: `tests/unit/test_key_router.py`
- Test: `tests/unit/test_mode_manager.py`

**Interfaces:**
- Produces: owned chord member-release suppression, first-release `KEY_UP`, final-member long-press start, and reset cancellation.
- Preserves: `KeyEventRouter.handle(...) -> AppKeyEventResult` and `ModeManager` reset calls on activation/exit.

- [ ] **Step 1: Write failing ownership and key-up tests**

```python
def test_handled_key_down_owns_all_member_key_ups():
    fallback = []
    up_calls = []
    router = KeyEventRouter(
        bindings=(
            binding({HID.A, HID.B}, KeyTrigger.KEY_DOWN, handled),
            binding({HID.A, HID.B}, KeyTrigger.KEY_UP,
                    lambda event: up_calls.append(event.usage)
                    or AppKeyEventResult.HANDLED_STOP),
        ),
        fallback=lambda event: fallback.append(event)
        or AppKeyEventResult.UNHANDLED,
    )

    router.handle(key(HID.A))
    router.handle(key(HID.B))
    assert router.handle(key(HID.A, False)) is AppKeyEventResult.HANDLED_STOP
    assert router.handle(key(HID.B, False)) is AppKeyEventResult.HANDLED_STOP
    assert up_calls == [HID.A]
    assert fallback == []
```

Add tests that a key-down handler returning `UNHANDLED` does not claim releases, while a chord with only a key-up binding claims its prefix downs and invokes key-up exactly once on first release.

- [ ] **Step 2: Write failing multi-key long-press tests**

Use the fake scheduler to assert:

```python
    router.handle(key(HID.A))
    assert scheduler.calls == []
    router.handle(key(HID.B))
    assert scheduler.calls[0][0] == 1.5
router.handle(key(HID.A))  # repeat
assert len(scheduler.calls) == 1
```

Fire the timer and assert one long handler call whose event usage is B, the key that completed the chord. Add cancellation tests for first member release, required modifier release, an extra C key causing exact mismatch, `reset()`, and mode exit through `ModeManager.exit_active_mode()`.

- [ ] **Step 3: Run ownership/long-press tests and verify RED**

Run: `pytest tests/unit/test_key_router.py tests/unit/test_mode_manager.py -q`

Expected: FAIL because the current router has no owned chord record and keys long-press state by one primary usage.

- [ ] **Step 4: Implement owned chord state**

Add:

```python
@dataclass(slots=True)
class _OwnedChord:
    chord: KeyChord
    physical_usages: set[int]
    key_up_binding: KeyBinding | None
    key_up_fired: bool = False
```

When an immediate key-down handler returns `HANDLED_STOP` or `HANDLED_CONTINUE`, create `_OwnedChord` from all currently held physical general/modifier usages. When a deferred shorter key-down handler resolves on release, ignore its result and always create ownership for its still-held/releasing members because their original downs were already suppressed. A chord with only `KEY_UP` creates ownership as soon as it becomes exact—before the no-candidate replay branch—and returns `HANDLED_STOP`. An immediate key-down result of `UNHANDLED` creates no ownership unless a `KEY_UP` binding independently requires it.

On the first owned member release, invoke `KEY_UP` once if present and return its result; mark it fired. Every later owned member release returns `HANDLED_STOP`. Never replay owned inputs to fallback.

- [ ] **Step 5: Generalize pending long-press state by chord**

Replace the singular-usage pending record with:

```python
@dataclass(slots=True)
class _PendingLongPress:
    chord: KeyChord
    completion_event: KeyEvent
    physical_usages: set[int]
    timer: ScheduledCall
    key_down_binding: KeyBinding | None
    long_press_binding: KeyBinding
    fired: bool = False
```

Schedule only when the complete exact chord first forms. Ignore repeat downs. On timer fire, verify the current exact chord still equals the pending chord, set `fired`, invoke the handler once, ignore its result, and establish ownership so later member releases cannot reach fallback. Cancel on any member release before deadline, required modifier loss, extra general/modifier key, or reset.

- [ ] **Step 6: Run all router/mode tests and verify GREEN**

Run: `pytest tests/unit/test_key_router.py tests/unit/test_mode_manager.py -q`

Expected: PASS.

- [ ] **Step 7: Commit ownership and lifecycle behavior**

```bash
git add src/accessibility_toolkit/input/router.py tests/unit/test_key_router.py tests/unit/test_mode_manager.py
git commit -m "feat: own multi-key chord lifecycles"
```

### Task 5: Verify app compatibility and finalize documentation

**Files:**
- Modify: `docs/superpowers/specs/2026-07-12-mode-key-router-design_zh-TW.md`
- Modify: `docs/superpowers/plans/2026-07-12-mode-key-router.md`
- Test: `tests/unit/test_key_echo_app_service.py`
- Test: `tests/unit/test_nvda_remote_app_service.py`
- Test: `tests/unit/test_access8graph_app_service.py`

**Interfaces:**
- Verifies: Access8Graph static bindings, Key Echo fallback, NVDA Remote raw HID/native fallback, and F11 exit key-up suppression.

- [x] **Step 1: Add a raw-event NVDA Remote regression test if not already covered**

```python
def test_nvda_remote_fallback_preserves_physical_modifier_and_native_context():
    service, transport, _capture, _hotkey, _dispatch = build_service(
        use_windows_native_key_payload=True
    )
    service.state.connection_state = ConnectionState.CONNECTED
    service.start_control()
    context = WindowsNativeKeyContext(
        vk_code=0xA3,
        scan_code=0x1D,
        extended=True,
    )

    service.handle_key_event(
        CapturedKeyEvent(
            key_event=KeyEvent(HID.KEYBOARD_PAGE, HID.RIGHT_CONTROL, True),
            native_context=context,
        )
    )

    assert transport.sent[-1][1]["vk_code"] == 0xA3
```

Use the existing test fixture constructors and exact transport payload shape from `tests/unit/test_nvda_remote_app_service.py`; do not invent a second fake transport.

- [x] **Step 2: Run focused app regressions**

Run:

`pytest tests/unit/test_key_router.py tests/unit/test_mode_manager.py tests/unit/test_key_echo_app_service.py tests/unit/test_nvda_remote_app_service.py tests/unit/test_access8graph_input.py tests/unit/test_access8graph_use_cases.py -q`

Expected: PASS with no new failures.

- [x] **Step 3: Run full verification and record the known fixture baseline**

Run: `pytest tests/unit tests/integration -q`

Expected in this isolated worktree: router-related tests pass; exactly 14 existing tests fail only because ignored `Access8Graph/tests/test.graphml` is absent. Any different failure blocks completion.

Run: `git diff --check`

Expected: no output and exit code 0.

- [x] **Step 4: Self-review spec and plan consistency**

Run:

```bash
rg -n "TBD|TODO|implement later|fill in details|appropriate error handling|Similar to Task" \
  docs/superpowers/specs/2026-07-12-mode-key-router-design_zh-TW.md \
  docs/superpowers/plans/2026-07-12-mode-key-router.md
rg -n "class KeyChord|class KeyEventRouter|class _PendingLongPress|class _OwnedChord" \
  src/accessibility_toolkit/input/router.py
```

Expected: the placeholder scan has no matches; every planned type exists after implementation.

- [x] **Step 5: Commit documentation and final regression test**

```bash
git add docs/superpowers/specs/2026-07-12-mode-key-router-design_zh-TW.md \
  docs/superpowers/plans/2026-07-12-mode-key-router.md \
  tests/unit/test_nvda_remote_app_service.py
git commit -m "docs: finalize multi-key router design"
```

## Plan self-review

- Task 1 covers optional/default scheduling and injected GUI scheduler compatibility.
- Tasks 2–4 cover every `KeyChord`, exact matching, prefix buffering, fallback replay, ownership, key-up, repeat, reset, and long-press requirement in the spec.
- Task 5 covers unchanged app behavior, raw NVDA Remote HID/native context, known fixture failures, and documentation consistency.
- All public names and signatures used by later tasks are defined before use; no dynamic binding API or unrelated platform capture refactor is introduced.
