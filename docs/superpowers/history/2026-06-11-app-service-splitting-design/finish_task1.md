# Review Fix Report — key_echo Hotkey State Guards & Capture Init

**Date:** 2026-06-11  
**Reviews:** `docs/superpowers/review_task0.md`, `docs/superpowers/review_task1.md`  
**Based on:** `docs/superpowers/specs/2026-06-11-app-service-splitting-design.md`

---

## Round 1 (`review_task0.md`)

### Issues Found

#### High: Enter hotkey unreachable at runtime

`build_runtime()` created and `bind()`-ed `KeyboardInputService` but never called `start()`. The capture was not running, so `handle_key_event()` never received `Enter` in the idle state. Enter could only be captured after echo was already running — creating a chicken-and-egg problem. The spec requirement "*Enter while not echoing -> enter echo mode*" was unreachable.

#### Medium: No state guards on Enter/Escape hotkeys

`handle_key_event()` unconditionally mapped Enter → `start_echo()` and Escape → `stop_echo()`, without checking current echo state. This meant:
- Enter was always consumed as a hotkey, never spoken during echo
- Escape was consumed even when echo was not running

The spec defines conditional transitions: Enter only starts when NOT echoing, Escape only stops when echoing.

### Fixes Applied

#### 1. Always-on capture (`src/apps/key_echo/main.py`)

```python
# Before
input_service.bind()
# After  
input_service.start()
```

`start()` calls `bind()` + `capture.start()`, so capture is always listening for hotkeys.

#### 2. Decoupled echo-active from capture-running (`src/apps/key_echo/use_cases/echo_control.py`)

Added `_echo_active` flag. `start_echo()` starts capture if needed + sets flag. `stop_echo()` only clears flag (does not stop capture — needed for Enter hotkey). `is_running()` returns `_echo_active`.

#### 3. State-guarded handle_key_event (`src/apps/key_echo/facade.py`)

```python
def handle_key_event(self, event):
    action = self._state_transition_hotkeys.match(event)
    if action == KeyEchoHotkeyAction.START_ECHO and not self.is_echo_running():
        self.start_echo()
        return SUPPRESS
    if action == KeyEchoHotkeyAction.STOP_ECHO and self.is_echo_running():
        self.stop_echo()
        return SUPPRESS
    if self.is_echo_running():
        return self._echo_input.handle(event)
    return PASS_THROUGH
```

#### 4. Updated tests

| Test | Change |
|------|--------|
| `test_key_echo_app_service_speaks_vk_on_keydown` | Added `attach_input_service` + `start_echo` before key event |
| `test_key_echo_app_service_ignores_keyup_for_speech` | Same |
| `test_key_echo_app_service_stops_echo_on_escape_keydown` | Removed `capture.stop_calls` assertion |
| `test_key_echo_app_service_starts_and_stops_echo_capture` | Replaced capture start/stop assertions with `is_echo_running()` checks |
| `test_key_echo_app_service_starts_echo_on_enter_keydown` | Removed `capture.start_calls` assertion |
| `test_key_echo_app_service_enter_keyup_does_not_duplicate_start` | Removed `capture.start_calls` assertion, added `is_echo_running()` check |
| `test_build_runtime_composes_local_keyboard_and_speech` | Expect `PASS_THROUGH` instead of `SUPPRESS`, empty speech output |
| `test_build_runtime_macos_path_composes_capture` | Added `start`/`stop`/`running` to `FakeKeyboardInputService` |
| `test_echo_control_use_case_start_and_stop_echo` | `input_service.stopped == 0`, added `is_running()` assertion |

### Post-Fix Behavior (Round 1)

| Key | Echo running? | Result |
|-----|--------------|--------|
| Enter | No | Start echo → SUPPRESS |
| Enter | Yes | Speak "VK 13" → SUPPRESS |
| Escape | No | PASS_THROUGH |
| Escape | Yes | Stop echo → SUPPRESS |
| Other | No | PASS_THROUGH |
| Other | Yes | Speak VK → SUPPRESS |

### Commit (Round 1)

```
1978b93 fix: guard key_echo hotkeys with state and start capture at init
```

---

## Round 2 (`review_task1.md`)

### Issue Found

#### Medium: Capture not stopped on shutdown

The always-on capture fix started `input_service` at app init, but `stop_echo()` only clears `_echo_active` and no longer calls `input_service.stop()`. `shutdown()` called `stop_echo()` + speech shutdown, but never stopped the input service. Capture (keyboard hook / event tap) remained running after app exit.

### Fix Applied

#### Stop input_service in shutdown (`src/apps/key_echo/facade.py`)

```python
# Before
def shutdown(self):
    self.stop_echo()
    self._outputs.speech.shutdown()

# After
def shutdown(self):
    self.stop_echo()
    if self._input_service is not None and self._input_service.running:
        self._input_service.stop()
    self._outputs.speech.shutdown()
```

### Verification

```
before shutdown: capture running = True
after shutdown: capture running = False
```

### Commit (Round 2)

```
2988f79 fix: stop input capture on key_echo shutdown
```

---

## Final Test Results

```
240 passed (unit + integration)
```
