# Bootstrap Layer Extraction Design

## Purpose

Extract shared platform adapter resolution and process-level bootstrap logic from both app entrypoints (`src/apps/nvda_remote/main.py`, `src/apps/key_echo/main.py`) into a reusable `src/bootstrap/` layer. This is Phase 1 of the broader SOLID refactor, targeting the highest-leverage duplication first.

## Scope

| In scope | Out of scope |
|----------|-------------|
| Platform adapter resolution (input capture, hotkey, clipboard, speech backend options) | Full provider/registry pattern (deferred to Phase 3 output architecture) |
| Process bootstrap (logging setup, config/log path policy) | Output channel redesign (tone/wave/braille) |
| Eliminating lazy-import duplication across two main.py files | Splitting NvdaRemoteAppService (deferred to Phase 2) |
| `_NullInputCapture` / `_NullHotkeyCapture` safe fallback for unsupported platforms | Typed domain events (deferred to Phase 1 follow-up) |

## Module Structure

```
src/bootstrap/
  __init__.py
  platform.py    # adapter factory functions
  runtime.py     # process-level initialization helpers
```

### `platform.py`

Pure functions only. All platform branching (`sys.platform`) and lazy imports (`importlib.import_module`) are encapsulated here. No classes.

**Public API:**

```python
from adapters.inputs.base import InputCapture, HotkeyCapture
from application.services import ClipboardService
from application.output_scheduler import OutputScheduler
from application.speech_backends import SpeechBackendOption

def create_input_capture() -> InputCapture: ...
def create_hotkey_capture() -> HotkeyCapture: ...
def create_clipboard_service() -> ClipboardService: ...
def default_speech_backend_options(scheduler: OutputScheduler) -> tuple[SpeechBackendOption, ...]: ...
def default_speech_backend_id() -> str: ...
```

**Internal design:**

- macOS `InputCapture` and `HotkeyCapture` share a single `EventTapManager` instance via module-level lazy init cache (`_macos_event_tap_manager`).
- All adapter classes are lazily imported via private `_get_*` functions with module-level global cache variables (same pattern as current main.py).
- Platform detection uses a single `_PLATFORM = sys.platform` constant.

**Fallback behavior per capability:**

| Capability | Windows | macOS | Other |
|-----------|---------|-------|-------|
| InputCapture | `WindowsKeyboardCapture()` | `MacOSKeyboardCapture(manager)` | `_NullInputCapture()` |
| HotkeyCapture | `WindowsHotkeyCapture()` | `MacOSHotkeyCapture(manager)` | `_NullHotkeyCapture()` |
| ClipboardService | `WindowsClipboardService()` | `_UnsupportedClipboardService()` | `_UnsupportedClipboardService()` |
| SpeechBackendOption | nvda_controller + pyttsx3 | pyttsx3 only | pyttsx3 only |

`_NullInputCapture` and `_NullHotkeyCapture` implement their respective protocols, with `start()` logging a warning instead of crashing. `_UnsupportedClipboardService` is moved out of `nvda_remote/main.py` into `platform.py` (it was already a generic fallback).

### `runtime.py`

Process-level initialization. No dependency on platform adapters or application services.

**Public API:**

```python
from pathlib import Path

def configure_logging(log_path: Path | None = None, app_name: str = "nvda-remote-client") -> Path: ...
def default_log_path(app_name: str = "nvda-remote-client") -> Path: ...
def default_config_path(app_name: str = "nvda-remote-client") -> Path: ...
```

**Path policy (unchanged from current behavior):**

- Frozen + macOS: `~/Library/Logs/{app_name}/{app_name}.log`, `~/Library/Application Support/{app_name}/{app_name}.json`
- Frozen + other: `{sys.executable.parent}/{app_name}.log`, `{sys.executable.parent}/{app_name}.json`
- Dev (not frozen): `{cwd}/{app_name}.log`, `{cwd}/{app_name}.json`

**`configure_logging` behavior (unchanged):**
- Creates file handler at log_path with DEBUG level and standard format
- Falls back to console logging if file logging fails
- Returns the log_path used

## Migration Plan

1. Create `src/bootstrap/__init__.py`, `platform.py`, `runtime.py`
2. Rewrite `nvda_remote/main.py` `build_runtime()` to use `platform.py` / `runtime.py`
3. Rewrite `key_echo/main.py` `build_runtime()` to use `platform.py`
4. Delete all duplicate helpers from both main.py files:
   - Lazy import helpers (`_get_windows_*_class`, `_get_nvda_controller_*`, `_get_macos_*`, `_load_macos_*`)
   - `_build_input_adapters`, `_build_clipboard_service`, `_build_macos_event_tap_manager`
   - `_default_backend_options`, `default_log_path`, `default_config_path`, `configure_logging`
   - Module-level global lazy-cache variables
5. Run `pytest tests/unit tests/integration -v`

## What Stays In main.py

- `NvdaRemoteRuntime` / `KeyEchoRuntime` dataclasses (app-specific)
- `build_runtime()` function (app-specific wiring, but now calls into bootstrap for adapters)
- `main()` entrypoint
- The `_is_frozen()` helper (moves to `runtime.py` as private)

## What Does NOT Change

- `SpeechBackendConfigStore` stays in `application/config.py`
- `NvdaRemoteAppService` / `KeyEchoAppService` stay in their respective service.py files
- `OutputScheduler`, `SpeechService`, `QueuedOutputService` stay in `application/`
- `KeyboardInputService` stays in `application/keyboard.py`
- All adapter implementations in `adapters/windows/` and `adapters/macos/` are unchanged
- `InputCapture` / `HotkeyCapture` protocols in `adapters/inputs/base.py` are unchanged

## Future Evolution Path

This design creates a clean seam for later phases:

- `platform.py` functions can evolve into a `PlatformAdapterProvider` class in Phase 3 (output channels)
- `runtime.py` can absorb any future cross-app startup concerns
- `_Null*` fallbacks provide the pattern for future platform expansion (e.g. Linux)
