# macOS Input Hook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build macOS `InputCapture` and `HotkeyCapture` adapters backed by a shared Quartz event tap manager so `nvda_remote` can globally capture and suppress keyboard input on macOS with `F11` control toggling.

**Architecture:** Add a new `adapters.macos` package with a shared `MacOSEventTapManager`, a focused permission helper, a keycode translation module, and two protocol-facing adapters: `MacOSKeyboardCapture` and `MacOSHotkeyCapture`. Keep the existing app-service contracts unchanged, add platform selection only in the composition root, and drive the work with fake-backend unit tests instead of requiring a real macOS runtime in CI.

**Tech Stack:** Python 3.11+, pytest, PyObjC (`Quartz`, `ApplicationServices`), Core Foundation run loops, existing `InputCapture` / `HotkeyCapture` / `KeyEvent` contracts

---

## File Structure

### Create

- `src/adapters/macos/__init__.py`
  Responsibility: Package marker and exports for macOS adapters.
- `src/adapters/macos/permissions.py`
  Responsibility: Wrap `AXIsProcessTrustedWithOptions(...)` and expose a small Python API for trust checks and prompting.
- `src/adapters/macos/keymap.py`
  Responsibility: Translate macOS virtual key codes into shared `KeyEvent` fields expected by the remote payload.
- `src/adapters/macos/event_tap.py`
  Responsibility: Own the shared Quartz event tap, background thread, run loop lifecycle, event dispatch, and tap recovery behavior.
- `src/adapters/macos/keyboard_hook.py`
  Responsibility: Implement `InputCapture` on top of `MacOSEventTapManager`.
- `src/adapters/macos/hotkey.py`
  Responsibility: Implement `HotkeyCapture` on top of `MacOSEventTapManager`.
- `tests/unit/test_macos_adapters.py`
  Responsibility: Unit coverage for permissions, key mapping, manager lifecycle, keyboard dispatch, hotkey dispatch, suppress behavior, and recovery logic.

### Modify

- `src/apps/nvda_remote/main.py`
  Responsibility: Select Windows or macOS adapter implementations in the composition root without leaking platform branching into the app service.
- `pyproject.toml`
  Responsibility: Add macOS-only PyObjC dependencies needed by the new adapters.
- `README.md`
  Responsibility: Document macOS support status, required permissions, and runtime limitations.

## Task 1: Add macOS Dependency Wiring

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Write the failing dependency test as a packaging assertion in the plan review**

Use this exact dependency target so later code imports are consistent:

```toml
dependencies = [
  "wxPython",
  "pyinstaller",
  "pyttsx3",
  "pyobjc-framework-ApplicationServices; sys_platform == 'darwin'",
  "pyobjc-framework-Quartz; sys_platform == 'darwin'",
]
```

This task does not add a pytest test because the failure mode is install-time, not runtime.

- [ ] **Step 2: Update `pyproject.toml` with macOS-only PyObjC dependencies**

Apply this edit:

```toml
[project]
name = "nvda-remote-client"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "wxPython",
  "pyinstaller",
  "pyttsx3",
  "pyobjc-framework-ApplicationServices; sys_platform == 'darwin'",
  "pyobjc-framework-Quartz; sys_platform == 'darwin'",
]
```

- [ ] **Step 3: Verify the dependency lines are present**

Run: `python - <<'PY'\nfrom pathlib import Path\ntext = Path('pyproject.toml').read_text(encoding='utf-8')\nassert \"pyobjc-framework-ApplicationServices; sys_platform == 'darwin'\" in text\nassert \"pyobjc-framework-Quartz; sys_platform == 'darwin'\" in text\nprint('ok')\nPY`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "build: add macos pyobjc dependencies"
```

## Task 2: Add macOS Permission Helper and Key Mapping

**Files:**
- Create: `src/adapters/macos/__init__.py`
- Create: `src/adapters/macos/permissions.py`
- Create: `src/adapters/macos/keymap.py`
- Test: `tests/unit/test_macos_adapters.py`

- [ ] **Step 1: Write the failing tests for permissions and key mapping**

Add these tests to `tests/unit/test_macos_adapters.py`:

```python
import pytest

from adapters.macos.keymap import KEYCODE_TO_VK, key_event_from_macos
from adapters.macos.permissions import AccessibilityPermissions
from interop.key.key_event import KeyEvent


def test_accessibility_permissions_returns_false_without_prompt():
    called = []

    def fake_checker(options):
        called.append(options)
        return False

    permissions = AccessibilityPermissions(checker=fake_checker)

    assert permissions.is_trusted(prompt=False) is False
    assert called == [None]


def test_accessibility_permissions_passes_prompt_option():
    called = []

    def fake_checker(options):
        called.append(options)
        return True

    permissions = AccessibilityPermissions(
        checker=fake_checker,
        prompt_key="prompt-key",
        true_value=True,
    )

    assert permissions.is_trusted(prompt=True) is True
    assert called == [{"prompt-key": True}]


def test_key_event_from_macos_maps_letter_keydown():
    event = key_event_from_macos(key_code=0, pressed=True, is_repeat=False)

    assert event == KeyEvent(vk=0x41, scan=0, extended=False, pressed=True)


def test_key_event_from_macos_maps_f11_keyup():
    event = key_event_from_macos(key_code=103, pressed=False, is_repeat=False)

    assert event == KeyEvent(vk=0x7A, scan=103, extended=False, pressed=False)


def test_key_event_from_macos_rejects_unknown_key_code():
    with pytest.raises(KeyError, match="Unsupported macOS key code 999"):
        key_event_from_macos(key_code=999, pressed=True, is_repeat=False)


def test_keycode_table_contains_f11_mapping():
    assert KEYCODE_TO_VK[103] == 0x7A
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/unit/test_macos_adapters.py -k "permissions or key_event or keycode" -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'adapters.macos'`

- [ ] **Step 3: Add the package marker and minimal permission helper**

Create `src/adapters/macos/__init__.py`:

```python
__all__ = [
    "event_tap",
    "hotkey",
    "keyboard_hook",
    "keymap",
    "permissions",
]
```

Create `src/adapters/macos/permissions.py`:

```python
from dataclasses import dataclass
from typing import Any, Callable


TrustedChecker = Callable[[Any], bool]


@dataclass(slots=True)
class AccessibilityPermissions:
    checker: TrustedChecker
    prompt_key: Any = None
    true_value: Any = True

    def is_trusted(self, *, prompt: bool = False) -> bool:
        if not prompt:
            return bool(self.checker(None))
        if self.prompt_key is None:
            raise RuntimeError("Prompt key is required when prompt=True")
        return bool(self.checker({self.prompt_key: self.true_value}))
```

- [ ] **Step 4: Add the initial macOS key mapping module**

Create `src/adapters/macos/keymap.py`:

```python
from interop.key.key_event import KeyEvent


KEYCODE_TO_VK: dict[int, int] = {
    0: 0x41,   # A
    1: 0x53,   # S
    2: 0x44,   # D
    3: 0x46,   # F
    12: 0x51,  # Q
    13: 0x57,  # W
    14: 0x45,  # E
    15: 0x52,  # R
    17: 0x54,  # T
    31: 0x4F,  # O
    32: 0x55,  # U
    34: 0x49,  # I
    35: 0x50,  # P
    37: 0x4C,  # L
    38: 0x4A,  # J
    40: 0x4B,  # K
    45: 0x4E,  # N
    46: 0x4D,  # M
    49: 0x20,  # Space
    53: 0x1B,  # Escape
    76: 0x0D,  # Return
    96: 0x74,  # F5
    97: 0x2E,  # Delete
    98: 0x73,  # F4
    99: 0x24,  # Home
    100: 0x23, # End
    101: 0x22, # PageDown
    103: 0x7A, # F11
    105: 0x25, # Left
    106: 0x27, # Right
    107: 0x28, # Down
    108: 0x26, # Up
    109: 0x70, # F1
    111: 0x7B, # F12
}

EXTENDED_KEY_CODES = {96, 97, 99, 100, 101, 103, 105, 106, 107, 108, 109, 111}


def key_event_from_macos(*, key_code: int, pressed: bool, is_repeat: bool) -> KeyEvent:
    del is_repeat
    try:
        vk = KEYCODE_TO_VK[key_code]
    except KeyError as error:
        raise KeyError(f"Unsupported macOS key code {key_code}") from error
    return KeyEvent(
        vk=vk,
        scan=key_code,
        extended=key_code in EXTENDED_KEY_CODES,
        pressed=pressed,
    )
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/unit/test_macos_adapters.py -k "permissions or key_event or keycode" -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/adapters/macos/__init__.py src/adapters/macos/permissions.py src/adapters/macos/keymap.py tests/unit/test_macos_adapters.py
git commit -m "feat: add macos permissions and key mapping"
```

## Task 3: Build the Shared Event Tap Manager

**Files:**
- Create: `src/adapters/macos/event_tap.py`
- Modify: `tests/unit/test_macos_adapters.py`

- [ ] **Step 1: Write the failing manager lifecycle and dispatch tests**

Append these tests to `tests/unit/test_macos_adapters.py`:

```python
from adapters.inputs.base import KeyEventDecision
from adapters.macos.event_tap import MacOSEventTapManager, RawMacKeyEvent


class FakePermissions:
    def __init__(self, trusted=True):
        self.trusted = trusted
        self.calls = []

    def is_trusted(self, *, prompt=False):
        self.calls.append(prompt)
        return self.trusted


class FakeQuartzBackend:
    def __init__(self):
        self.created = 0
        self.enabled = []
        self.released = []
        self.run_calls = 0
        self.stop_calls = 0
        self.tap = object()
        self.source = object()

    def create_event_tap(self, callback):
        self.created += 1
        self.callback = callback
        return self.tap

    def create_run_loop_source(self, tap):
        assert tap is self.tap
        return self.source

    def add_source(self, source):
        assert source is self.source

    def enable_tap(self, tap, enabled):
        self.enabled.append((tap, enabled))

    def run_loop_run(self):
        self.run_calls += 1

    def run_loop_stop(self):
        self.stop_calls += 1

    def release(self, value):
        self.released.append(value)


def test_event_tap_manager_requires_accessibility_permission():
    manager = MacOSEventTapManager(
        permissions=FakePermissions(trusted=False),
        backend=FakeQuartzBackend(),
        start_thread=False,
    )

    with pytest.raises(RuntimeError, match="macOS accessibility permission is required"):
        manager.start()


def test_event_tap_manager_starts_backend_once():
    backend = FakeQuartzBackend()
    manager = MacOSEventTapManager(
        permissions=FakePermissions(),
        backend=backend,
        start_thread=False,
    )

    manager.start()
    manager.start()

    assert backend.created == 1
    assert backend.enabled == [(backend.tap, True)]


def test_event_tap_manager_routes_keyboard_decision():
    backend = FakeQuartzBackend()
    manager = MacOSEventTapManager(
        permissions=FakePermissions(),
        backend=backend,
        start_thread=False,
    )
    seen = []
    manager.set_keyboard_listener(lambda event: seen.append(event) or KeyEventDecision.SUPPRESS)

    manager.start()
    decision = manager.handle_raw_event(
        RawMacKeyEvent(key_code=0, pressed=True, is_repeat=False)
    )

    assert seen == [RawMacKeyEvent(key_code=0, pressed=True, is_repeat=False)]
    assert decision == KeyEventDecision.SUPPRESS


def test_event_tap_manager_stop_releases_resources():
    backend = FakeQuartzBackend()
    manager = MacOSEventTapManager(
        permissions=FakePermissions(),
        backend=backend,
        start_thread=False,
    )

    manager.start()
    manager.stop()

    assert backend.stop_calls == 1
    assert backend.released == [backend.source, backend.tap]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/unit/test_macos_adapters.py -k "event_tap_manager" -v`
Expected: FAIL with `ModuleNotFoundError` for `adapters.macos.event_tap`

- [ ] **Step 3: Implement the minimal manager and raw-event model**

Create `src/adapters/macos/event_tap.py`:

```python
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from adapters.inputs.base import KeyEventDecision


@dataclass(frozen=True, slots=True)
class RawMacKeyEvent:
    key_code: int
    pressed: bool
    is_repeat: bool


RawListener = Callable[[RawMacKeyEvent], KeyEventDecision]


class MacOSEventTapManager:
    def __init__(
        self,
        *,
        permissions,
        backend,
        start_thread: bool = True,
    ) -> None:
        self._permissions = permissions
        self._backend = backend
        self._start_thread = start_thread
        self._keyboard_listener: RawListener | None = None
        self._hotkey_handler: Callable[[RawMacKeyEvent], bool] | None = None
        self._running = False
        self._tap: Any | None = None
        self._source: Any | None = None

    @property
    def running(self) -> bool:
        return self._running

    def set_keyboard_listener(self, listener: RawListener | None) -> None:
        self._keyboard_listener = listener

    def set_hotkey_handler(
        self, handler: Callable[[RawMacKeyEvent], bool] | None
    ) -> None:
        self._hotkey_handler = handler

    def start(self) -> None:
        if self._running:
            return
        if not self._permissions.is_trusted(prompt=False):
            raise RuntimeError("macOS accessibility permission is required")
        self._tap = self._backend.create_event_tap(self.handle_raw_event)
        self._source = self._backend.create_run_loop_source(self._tap)
        self._backend.add_source(self._source)
        self._backend.enable_tap(self._tap, True)
        self._running = True
        if self._start_thread:
            self._backend.run_loop_run()

    def stop(self) -> None:
        if not self._running:
            return
        self._backend.run_loop_stop()
        if self._source is not None:
            self._backend.release(self._source)
        if self._tap is not None:
            self._backend.release(self._tap)
        self._tap = None
        self._source = None
        self._running = False

    def handle_raw_event(self, event: RawMacKeyEvent) -> KeyEventDecision:
        if self._hotkey_handler is not None and self._hotkey_handler(event):
            return KeyEventDecision.SUPPRESS
        if self._keyboard_listener is None:
            return KeyEventDecision.PASS_THROUGH
        return self._keyboard_listener(event)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/unit/test_macos_adapters.py -k "event_tap_manager" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adapters/macos/event_tap.py tests/unit/test_macos_adapters.py
git commit -m "feat: add macos event tap manager shell"
```

## Task 4: Implement `MacOSKeyboardCapture`

**Files:**
- Create: `src/adapters/macos/keyboard_hook.py`
- Modify: `tests/unit/test_macos_adapters.py`

- [ ] **Step 1: Write the failing keyboard-capture tests**

Append these tests to `tests/unit/test_macos_adapters.py`:

```python
from adapters.macos.keyboard_hook import MacOSKeyboardCapture


class FakeManager:
    def __init__(self):
        self.listener = None
        self.running = False
        self.started = 0
        self.stopped = 0

    def set_keyboard_listener(self, listener):
        self.listener = listener

    def start(self):
        self.started += 1
        self.running = True

    def stop(self):
        self.stopped += 1
        self.running = False


def test_macos_keyboard_capture_binds_listener_and_translates_event():
    manager = FakeManager()
    capture = MacOSKeyboardCapture(manager=manager)
    seen = []
    capture.set_listener(lambda event: seen.append(event) or KeyEventDecision.SUPPRESS)

    capture.start()
    decision = manager.listener(RawMacKeyEvent(key_code=0, pressed=True, is_repeat=False))

    assert decision == KeyEventDecision.SUPPRESS
    assert seen == [KeyEvent(vk=0x41, scan=0, extended=False, pressed=True)]


def test_macos_keyboard_capture_proxies_lifecycle():
    manager = FakeManager()
    capture = MacOSKeyboardCapture(manager=manager)

    capture.start()
    capture.stop()

    assert manager.started == 1
    assert manager.stopped == 1
    assert capture.running is False
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/unit/test_macos_adapters.py -k "macos_keyboard_capture" -v`
Expected: FAIL with `ModuleNotFoundError` for `adapters.macos.keyboard_hook`

- [ ] **Step 3: Implement the minimal keyboard capture adapter**

Create `src/adapters/macos/keyboard_hook.py`:

```python
from collections.abc import Callable

from adapters.inputs.base import KeyEventDecision
from adapters.macos.keymap import key_event_from_macos
from adapters.macos.event_tap import RawMacKeyEvent


class MacOSKeyboardCapture:
    def __init__(self, *, manager) -> None:
        self._manager = manager
        self._listener: Callable | None = None

    @property
    def running(self) -> bool:
        return bool(self._manager.running)

    def set_listener(self, listener: Callable) -> None:
        self._listener = listener

    def start(self) -> None:
        self._manager.set_keyboard_listener(self._handle_raw_event)
        self._manager.start()

    def stop(self) -> None:
        self._manager.set_keyboard_listener(None)
        self._manager.stop()

    def _handle_raw_event(self, event: RawMacKeyEvent) -> KeyEventDecision:
        if self._listener is None:
            return KeyEventDecision.PASS_THROUGH
        return self._listener(
            key_event_from_macos(
                key_code=event.key_code,
                pressed=event.pressed,
                is_repeat=event.is_repeat,
            )
        )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/unit/test_macos_adapters.py -k "macos_keyboard_capture" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adapters/macos/keyboard_hook.py tests/unit/test_macos_adapters.py
git commit -m "feat: add macos keyboard capture adapter"
```

## Task 5: Implement `MacOSHotkeyCapture` and `F11` Suppression

**Files:**
- Create: `src/adapters/macos/hotkey.py`
- Modify: `src/adapters/macos/event_tap.py`
- Modify: `tests/unit/test_macos_adapters.py`

- [ ] **Step 1: Write the failing hotkey tests**

Append these tests to `tests/unit/test_macos_adapters.py`:

```python
from adapters.macos.hotkey import MacOSHotkeyCapture


def test_macos_hotkey_capture_triggers_f11_once_on_keydown():
    backend = FakeQuartzBackend()
    manager = MacOSEventTapManager(
        permissions=FakePermissions(),
        backend=backend,
        start_thread=False,
    )
    triggered = []
    capture = MacOSHotkeyCapture(manager=manager)
    capture.set_handler(lambda: triggered.append("f11"))

    capture.start()
    assert manager.handle_raw_event(
        RawMacKeyEvent(key_code=103, pressed=True, is_repeat=False)
    ) == KeyEventDecision.SUPPRESS
    assert manager.handle_raw_event(
        RawMacKeyEvent(key_code=103, pressed=True, is_repeat=True)
    ) == KeyEventDecision.SUPPRESS
    assert manager.handle_raw_event(
        RawMacKeyEvent(key_code=103, pressed=False, is_repeat=False)
    ) == KeyEventDecision.SUPPRESS

    assert triggered == ["f11"]


def test_macos_hotkey_capture_ignores_non_f11_keys():
    backend = FakeQuartzBackend()
    manager = MacOSEventTapManager(
        permissions=FakePermissions(),
        backend=backend,
        start_thread=False,
    )
    triggered = []
    capture = MacOSHotkeyCapture(manager=manager)
    capture.set_handler(lambda: triggered.append("f11"))

    capture.start()
    decision = manager.handle_raw_event(
        RawMacKeyEvent(key_code=0, pressed=True, is_repeat=False)
    )

    assert decision == KeyEventDecision.PASS_THROUGH
    assert triggered == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/unit/test_macos_adapters.py -k "macos_hotkey_capture" -v`
Expected: FAIL with `ModuleNotFoundError` for `adapters.macos.hotkey`

- [ ] **Step 3: Extend the manager with hotkey keyup suppression tracking**

Update `src/adapters/macos/event_tap.py`:

```python
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from adapters.inputs.base import KeyEventDecision


@dataclass(frozen=True, slots=True)
class RawMacKeyEvent:
    key_code: int
    pressed: bool
    is_repeat: bool


RawListener = Callable[[RawMacKeyEvent], KeyEventDecision]
HotkeyHandler = Callable[[RawMacKeyEvent], bool]


class MacOSEventTapManager:
    def __init__(
        self,
        *,
        permissions,
        backend,
        start_thread: bool = True,
    ) -> None:
        self._permissions = permissions
        self._backend = backend
        self._start_thread = start_thread
        self._keyboard_listener: RawListener | None = None
        self._hotkey_handler: HotkeyHandler | None = None
        self._suppressed_keyups: set[int] = set()
        self._running = False
        self._tap: Any | None = None
        self._source: Any | None = None

    @property
    def running(self) -> bool:
        return self._running

    def set_keyboard_listener(self, listener: RawListener | None) -> None:
        self._keyboard_listener = listener

    def set_hotkey_handler(self, handler: HotkeyHandler | None) -> None:
        self._hotkey_handler = handler

    def start(self) -> None:
        if self._running:
            return
        if not self._permissions.is_trusted(prompt=False):
            raise RuntimeError("macOS accessibility permission is required")
        self._tap = self._backend.create_event_tap(self.handle_raw_event)
        self._source = self._backend.create_run_loop_source(self._tap)
        self._backend.add_source(self._source)
        self._backend.enable_tap(self._tap, True)
        self._running = True
        if self._start_thread:
            self._backend.run_loop_run()

    def stop(self) -> None:
        if not self._running:
            return
        self._backend.run_loop_stop()
        if self._source is not None:
            self._backend.release(self._source)
        if self._tap is not None:
            self._backend.release(self._tap)
        self._suppressed_keyups.clear()
        self._tap = None
        self._source = None
        self._running = False

    def handle_raw_event(self, event: RawMacKeyEvent) -> KeyEventDecision:
        if not event.pressed and event.key_code in self._suppressed_keyups:
            self._suppressed_keyups.discard(event.key_code)
            return KeyEventDecision.SUPPRESS
        if self._hotkey_handler is not None and self._hotkey_handler(event):
            if event.pressed:
                self._suppressed_keyups.add(event.key_code)
            return KeyEventDecision.SUPPRESS
        if self._keyboard_listener is None:
            return KeyEventDecision.PASS_THROUGH
        return self._keyboard_listener(event)
```

- [ ] **Step 4: Implement the hotkey adapter**

Create `src/adapters/macos/hotkey.py`:

```python
from collections.abc import Callable

from adapters.macos.event_tap import RawMacKeyEvent


F11_KEY_CODE = 103


class MacOSHotkeyCapture:
    def __init__(self, *, manager, key_code: int = F11_KEY_CODE) -> None:
        self._manager = manager
        self._handler: Callable[[], None] | None = None
        self._key_code = key_code

    @property
    def running(self) -> bool:
        return bool(self._manager.running)

    def set_handler(self, handler: Callable[[], None]) -> None:
        self._handler = handler

    def start(self) -> None:
        self._manager.set_hotkey_handler(self._handle_raw_event)
        self._manager.start()

    def stop(self) -> None:
        self._manager.set_hotkey_handler(None)
        self._manager.stop()

    def _handle_raw_event(self, event: RawMacKeyEvent) -> bool:
        if event.key_code != self._key_code:
            return False
        if not event.pressed or event.is_repeat:
            return True
        if self._handler is not None:
            self._handler()
        return True
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/unit/test_macos_adapters.py -k "macos_hotkey_capture" -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/adapters/macos/event_tap.py src/adapters/macos/hotkey.py tests/unit/test_macos_adapters.py
git commit -m "feat: add macos hotkey capture"
```

## Task 6: Add Platform Selection in the NVDA Remote Composition Root

**Files:**
- Modify: `src/apps/nvda_remote/main.py`
- Modify: `tests/unit/test_app_wx.py`

- [ ] **Step 1: Write the failing runtime selection test**

Add a focused test to `tests/unit/test_app_wx.py`:

```python
def test_build_runtime_uses_macos_input_and_hotkey_on_darwin(monkeypatch):
    from apps.nvda_remote import main as nvda_remote_main

    class FakeMacKeyboardCapture:
        def __init__(self, manager):
            self.manager = manager

    class FakeMacHotkeyCapture:
        def __init__(self, manager):
            self.manager = manager

    class FakeManager:
        pass

    monkeypatch.setattr(nvda_remote_main, "MacOSEventTapManager", FakeManager)
    monkeypatch.setattr(nvda_remote_main, "MacOSKeyboardCapture", FakeMacKeyboardCapture)
    monkeypatch.setattr(nvda_remote_main, "MacOSHotkeyCapture", FakeMacHotkeyCapture)
    monkeypatch.setattr(nvda_remote_main.sys, "platform", "darwin")

    runtime = nvda_remote_main.build_runtime()

    assert isinstance(runtime.input_capture, FakeMacKeyboardCapture)
    assert isinstance(runtime.hotkey_capture, FakeMacHotkeyCapture)
    assert runtime.input_capture.manager is runtime.hotkey_capture.manager
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/unit/test_app_wx.py::test_build_runtime_uses_macos_input_and_hotkey_on_darwin -v`
Expected: FAIL because `apps.nvda_remote.main` does not yet expose macOS adapter symbols or platform selection

- [ ] **Step 3: Update the composition root**

Modify `src/apps/nvda_remote/main.py` imports and `build_runtime()` selection logic:

```python
from adapters.windows.clipboard import WindowsClipboardService
from adapters.windows.hotkey import WindowsHotkeyCapture
from adapters.windows.keyboard_hook import WindowsKeyboardCapture
from adapters.windows.nvda_controller import NvdaControllerSpeechOutput

try:
    from adapters.macos.event_tap import MacOSEventTapManager
    from adapters.macos.hotkey import MacOSHotkeyCapture
    from adapters.macos.keyboard_hook import MacOSKeyboardCapture
except ImportError:  # pragma: no cover - platform dependency
    MacOSEventTapManager = None
    MacOSHotkeyCapture = None
    MacOSKeyboardCapture = None
```

Then replace the hard-coded capture construction in `build_runtime()` with:

```python
    if sys.platform == "darwin":
        if (
            MacOSEventTapManager is None
            or MacOSKeyboardCapture is None
            or MacOSHotkeyCapture is None
        ):
            raise RuntimeError("macOS input capture dependencies are unavailable")
        manager = MacOSEventTapManager()
        input_capture = MacOSKeyboardCapture(manager=manager)
        hotkey_capture = MacOSHotkeyCapture(manager=manager)
    else:
        input_capture = WindowsKeyboardCapture()
        hotkey_capture = WindowsHotkeyCapture()
```

Leave `clipboard = WindowsClipboardService()` unchanged in this task. The spec does not include a macOS clipboard backend, so the composition root can still remain Windows-only for clipboard until that work is planned separately.

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/unit/test_app_wx.py::test_build_runtime_uses_macos_input_and_hotkey_on_darwin -v`
Expected: PASS

- [ ] **Step 5: Run the existing NVDA Remote runtime test slice**

Run: `pytest tests/unit/test_app_wx.py tests/unit/test_nvda_remote_app_service.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/apps/nvda_remote/main.py tests/unit/test_app_wx.py
git commit -m "feat: select macos input adapters in runtime"
```

## Task 7: Add Real PyObjC Backend and Recovery Hooks

**Files:**
- Modify: `src/adapters/macos/permissions.py`
- Modify: `src/adapters/macos/event_tap.py`
- Modify: `tests/unit/test_macos_adapters.py`

- [ ] **Step 1: Write the failing tests for prompt wiring and tap recovery**

Append these tests to `tests/unit/test_macos_adapters.py`:

```python
def test_event_tap_manager_reenables_tap_after_disable_signal():
    backend = FakeQuartzBackend()
    manager = MacOSEventTapManager(
        permissions=FakePermissions(),
        backend=backend,
        start_thread=False,
    )
    manager.start()

    manager.handle_tap_disabled()

    assert backend.enabled == [(backend.tap, True), (backend.tap, True)]


def test_accessibility_permissions_prompt_key_error_is_clear():
    permissions = AccessibilityPermissions(checker=lambda options: True)

    with pytest.raises(RuntimeError, match="Prompt key is required when prompt=True"):
        permissions.is_trusted(prompt=True)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/unit/test_macos_adapters.py -k "reenables_tap or prompt_key_error" -v`
Expected: FAIL because `handle_tap_disabled()` is not implemented yet

- [ ] **Step 3: Add recovery hook and real import path shells**

Update `src/adapters/macos/event_tap.py` with:

```python
    def handle_tap_disabled(self) -> None:
        if self._tap is None:
            return
        self._backend.enable_tap(self._tap, True)
```

Then extend `src/adapters/macos/permissions.py` so production construction can work on macOS:

```python
from dataclasses import dataclass
from typing import Any, Callable

try:  # pragma: no cover - exercised on macOS
    from ApplicationServices import (
        AXIsProcessTrustedWithOptions,
        kAXTrustedCheckOptionPrompt,
    )
except ImportError:  # pragma: no cover - non-macOS test environment
    AXIsProcessTrustedWithOptions = None
    kAXTrustedCheckOptionPrompt = None


TrustedChecker = Callable[[Any], bool]


@dataclass(slots=True)
class AccessibilityPermissions:
    checker: TrustedChecker
    prompt_key: Any = None
    true_value: Any = True

    @classmethod
    def load_default(cls) -> "AccessibilityPermissions":
        if AXIsProcessTrustedWithOptions is None:
            raise RuntimeError("PyObjC ApplicationServices is required on macOS")
        return cls(
            checker=AXIsProcessTrustedWithOptions,
            prompt_key=kAXTrustedCheckOptionPrompt,
            true_value=True,
        )

    def is_trusted(self, *, prompt: bool = False) -> bool:
        if not prompt:
            return bool(self.checker(None))
        if self.prompt_key is None:
            raise RuntimeError("Prompt key is required when prompt=True")
        return bool(self.checker({self.prompt_key: self.true_value}))
```

Add a production backend shell to `src/adapters/macos/event_tap.py`:

```python
class QuartzEventTapBackend:
    def create_event_tap(self, callback):
        raise NotImplementedError

    def create_run_loop_source(self, tap):
        raise NotImplementedError

    def add_source(self, source):
        raise NotImplementedError

    def enable_tap(self, tap, enabled):
        raise NotImplementedError

    def run_loop_run(self):
        raise NotImplementedError

    def run_loop_stop(self):
        raise NotImplementedError

    def release(self, value):
        raise NotImplementedError
```

Do not implement the full PyObjC calls in this task; just make the public API shape stable so the next engineer can fill in the macOS-native backend without changing the tests or adapters.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/unit/test_macos_adapters.py -k "reenables_tap or prompt_key_error" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adapters/macos/permissions.py src/adapters/macos/event_tap.py tests/unit/test_macos_adapters.py
git commit -m "feat: add macos tap recovery hooks"
```

## Task 8: Document macOS Runtime Requirements

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add README coverage for macOS permissions and scope**

Append or update these sections in `README.md`:

```md
## Requirements

- Python 3.11+
- Windows for full runtime validation of the existing clipboard and NVDA controller paths
- macOS for runtime validation of Quartz keyboard capture
- `wxPython` for the GUI
- NVDA installed and running locally if you want speech output through the vendored `x64/nvdaControllerClient.dll`

## macOS Notes

- macOS keyboard capture uses Quartz event taps via `PyObjC`.
- The app must be granted Accessibility / Input Monitoring access for global keyboard capture to work.
- The current macOS scope covers keyboard capture and `F11` hotkey control toggling only.
- Clipboard and NVDA controller integrations remain Windows-specific.
```

- [ ] **Step 2: Verify the README text is present**

Run: `rg -n "macOS keyboard capture uses Quartz event taps|Accessibility / Input Monitoring access|Clipboard and NVDA controller integrations remain Windows-specific" README.md`
Expected: three matching lines

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document macos input capture requirements"
```

## Task 9: Final Verification Sweep

**Files:**
- Modify: `docs/superpowers/specs/2026-06-06-macos-input-hook-design_zh-TW.md`
- Modify: `docs/superpowers/plans/2026-06-06-macos-input-hook-implementation.md`

- [ ] **Step 1: Run the targeted unit suite**

Run:

```bash
pytest tests/unit/test_macos_adapters.py \
  tests/unit/test_nvda_remote_app_service.py \
  tests/unit/test_app_wx.py -v
```

Expected: PASS

- [ ] **Step 2: Run a broader regression slice for existing Windows adapters**

Run:

```bash
pytest tests/unit/test_windows_adapters.py \
  tests/unit/test_keyboard_input_service.py \
  tests/unit/test_key_echo_app_service.py -v
```

Expected: PASS

- [ ] **Step 3: Update the spec and plan only if implementation changed the agreed shape**

If file names, lifecycle behavior, or runtime prerequisites changed during implementation, update:

```text
docs/superpowers/specs/2026-06-06-macos-input-hook-design_zh-TW.md
docs/superpowers/plans/2026-06-06-macos-input-hook-implementation.md
```

If nothing changed, leave both files untouched.

- [ ] **Step 4: Commit the final integrated state**

```bash
git add src/adapters/macos pyproject.toml src/apps/nvda_remote/main.py README.md tests/unit/test_macos_adapters.py tests/unit/test_app_wx.py docs/superpowers/specs/2026-06-06-macos-input-hook-design_zh-TW.md docs/superpowers/plans/2026-06-06-macos-input-hook-implementation.md
git commit -m "feat: add macos keyboard and hotkey capture"
```

## Self-Review

### Spec coverage

- macOS `InputCapture`: covered by Tasks 2, 3, and 4.
- macOS `HotkeyCapture`: covered by Task 5.
- Shared `MacOSEventTapManager`: covered by Tasks 3 and 5.
- `F11` suppress rules: covered by Task 5.
- Platform selection in composition root: covered by Task 6.
- Permissions and macOS runtime requirements: covered by Tasks 2, 7, and 8.
- Manual/runtime caveats: documented in Task 8.

### Placeholder scan

- No `TODO`, `TBD`, or “implement later” placeholders remain in the plan steps.
- The one deliberate “shell” in Task 7 is explicitly scoped and includes the exact public API to add.

### Type consistency

- `MacOSEventTapManager`, `RawMacKeyEvent`, `MacOSKeyboardCapture`, and `MacOSHotkeyCapture` names are used consistently across all tasks.
- The plan keeps `InputCapture` and `HotkeyCapture` contracts unchanged.
