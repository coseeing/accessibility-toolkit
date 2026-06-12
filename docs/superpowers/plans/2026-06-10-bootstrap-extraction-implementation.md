# Bootstrap Layer Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract shared platform adapter resolution and process-level bootstrap logic from both app entrypoints into `src/bootstrap/`.

**Architecture:** Create `src/bootstrap/platform.py` (adapter factory functions) and `src/bootstrap/runtime.py` (logging/path helpers), then strip duplicate helpers from both `main.py` files. All existing behavior is preserved; the change is purely structural.

**Tech Stack:** Python 3.12+, pytest, monkeypatch

---

### Task 1: Create `src/bootstrap/__init__.py`

**Files:**
- Create: `src/bootstrap/__init__.py`

- [ ] **Step 1: Create empty init file**

```bash
mkdir -p src/bootstrap
```

- [ ] **Step 2: Write `src/bootstrap/__init__.py`**

Write the file with content:

```python
```

- [ ] **Step 3: Commit**

```bash
git add src/bootstrap/__init__.py
git commit -m "feat: add bootstrap package init"
```

---

### Task 2: Write tests for `src/bootstrap/runtime.py`

**Files:**
- Create: `tests/unit/test_bootstrap_runtime.py`

- [ ] **Step 1: Write the test file**

```python
import logging
import sys
from pathlib import Path

import pytest

from bootstrap.runtime import (
    configure_logging,
    default_config_path,
    default_log_path,
)


class TestDefaultLogPath:
    def test_dev_uses_cwd(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", False, raising=False)
        cwd = Path.cwd().resolve()

        result = default_log_path(app_name="test-app")

        assert result == cwd / "test-app.log"

    def test_dev_uses_default_app_name(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", False, raising=False)
        cwd = Path.cwd().resolve()

        result = default_log_path()

        assert result == cwd / "nvda-remote-client.log"

    def test_frozen_darwin_logs_dir(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "platform", "darwin")

        result = default_log_path(app_name="my-app")

        assert result == Path.home() / "Library" / "Logs" / "my-app" / "my-app.log"

    def test_frozen_non_darwin_uses_executable_parent(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(sys, "executable", "/opt/my-app/app.exe")

        result = default_log_path(app_name="my-app")

        assert result == Path("/opt/my-app") / "my-app.log"


class TestDefaultConfigPath:
    def test_dev_uses_cwd(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", False, raising=False)
        cwd = Path.cwd().resolve()

        result = default_config_path(app_name="test-app")

        assert result == cwd / "test-app.json"

    def test_frozen_darwin_app_support_dir(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "platform", "darwin")

        result = default_config_path(app_name="my-app")

        assert result == Path.home() / "Library" / "Application Support" / "my-app" / "my-app.json"

    def test_frozen_non_darwin_uses_executable_parent(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(sys, "executable", "/opt/my-app/app.exe")

        result = default_config_path(app_name="my-app")

        assert result == Path("/opt/my-app") / "my-app.json"


class TestConfigureLogging:
    def test_returns_log_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sys, "frozen", False, raising=False)
        log_path = tmp_path / "test.log"

        result = configure_logging(log_path=log_path)

        assert result == log_path
        assert log_path.exists()

    def test_uses_warning_level(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr(sys, "frozen", False, raising=False)
        log_path = tmp_path / "test.log"

        configure_logging(log_path=log_path)

        test_logger = logging.getLogger("test_configure")
        test_logger.warning("hello bootstrap")

        content = log_path.read_text(encoding="utf-8")
        assert "hello bootstrap" in content
```

- [ ] **Step 2: Run tests, expect FAIL (module not found)**

```bash
PYTHONPATH=src python -m pytest tests/unit/test_bootstrap_runtime.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'bootstrap.runtime'`

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_bootstrap_runtime.py
git commit -m "test: add bootstrap runtime unit tests"
```

---

### Task 3: Implement `src/bootstrap/runtime.py`

**Files:**
- Create: `src/bootstrap/runtime.py`

- [ ] **Step 1: Write `src/bootstrap/runtime.py`**

```python
import logging
from pathlib import Path
import sys


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _macos_app_support_dir(app_name: str) -> Path:
    return Path.home() / "Library" / "Application Support" / app_name


def _macos_logs_dir(app_name: str) -> Path:
    return Path.home() / "Library" / "Logs" / app_name


def default_log_path(app_name: str = "nvda-remote-client") -> Path:
    if _is_frozen():
        if sys.platform == "darwin":
            return _macos_logs_dir(app_name) / f"{app_name}.log"
        return Path(sys.executable).resolve().parent / f"{app_name}.log"
    return Path.cwd().resolve() / f"{app_name}.log"


def default_config_path(app_name: str = "nvda-remote-client") -> Path:
    if _is_frozen():
        if sys.platform == "darwin":
            return _macos_app_support_dir(app_name) / f"{app_name}.json"
        return Path(sys.executable).resolve().parent / f"{app_name}.json"
    return Path.cwd().resolve() / f"{app_name}.json"


def configure_logging(
    log_path: Path | None = None,
    app_name: str = "nvda-remote-client",
) -> Path:
    if log_path is None:
        log_path = default_log_path(app_name)
    log_format = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    root_logger = logging.getLogger()
    try:
        if not root_logger.handlers:
            logging.basicConfig(
                level=logging.DEBUG,
                format=log_format,
                filename=log_path,
                filemode="a",
            )
        else:
            file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter(log_format))
            root_logger.addHandler(file_handler)
        logging.getLogger(__name__).info("Logging initialized at %s", log_path)
    except OSError as error:
        if not root_logger.handlers:
            logging.basicConfig(
                level=logging.DEBUG,
                format=log_format,
            )
        logging.getLogger(__name__).warning(
            "File logging unavailable at %s: %s",
            log_path,
            error,
        )
    return log_path
```

- [ ] **Step 2: Run runtime tests, expect PASS**

```bash
PYTHONPATH=src python -m pytest tests/unit/test_bootstrap_runtime.py -v
```

Expected: all tests PASS

- [ ] **Step 3: Commit**

```bash
git add src/bootstrap/runtime.py
git commit -m "feat: add bootstrap/runtime.py with logging and path helpers"
```

---

### Task 4: Write tests for `src/bootstrap/platform.py`

**Files:**
- Create: `tests/unit/test_bootstrap_platform.py`

- [ ] **Step 1: Write the test file**

```python
import logging
import sys

from bootstrap.platform import (
    create_input_capture,
    create_hotkey_capture,
    create_clipboard_service,
    default_speech_backend_id,
    default_speech_backend_options,
)


class TestDefaultSpeechBackendId:
    def test_windows_returns_nvda_controller(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "win32")
        assert default_speech_backend_id() == "nvda_controller"

    def test_darwin_returns_pyttsx3(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "darwin")
        assert default_speech_backend_id() == "pyttsx3"

    def test_other_platform_returns_pyttsx3(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        assert default_speech_backend_id() == "pyttsx3"


class TestDefaultSpeechBackendOptions:
    def test_windows_includes_nvda_controller_and_pyttsx3(self, monkeypatch):
        from application.output_scheduler import OutputScheduler

        monkeypatch.setattr(sys, "platform", "win32")
        scheduler = OutputScheduler()
        try:
            options = default_speech_backend_options(scheduler)
            ids = [opt.backend_id for opt in options]
            assert ids == ["nvda_controller", "pyttsx3"]
        finally:
            scheduler.shutdown()

    def test_non_windows_includes_only_pyttsx3(self, monkeypatch):
        from application.output_scheduler import OutputScheduler

        monkeypatch.setattr(sys, "platform", "darwin")
        scheduler = OutputScheduler()
        try:
            options = default_speech_backend_options(scheduler)
            ids = [opt.backend_id for opt in options]
            assert ids == ["pyttsx3"]
        finally:
            scheduler.shutdown()


class TestCreateInputCapture:
    def test_unsupported_platform_returns_null_capture(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        capture = create_input_capture()

        assert not capture.running
        capture.stop()


class TestCreateHotkeyCapture:
    def test_unsupported_platform_returns_null_capture(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        capture = create_hotkey_capture()

        assert not capture.running
        capture.stop()


class TestCreateClipboardService:
    def test_unsupported_platform_returns_fallback(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        clipboard = create_clipboard_service()

        assert clipboard.get_text() == ""
        clipboard.set_text("test")
        assert clipboard.get_text() == ""


class TestNullInputCapture:
    def test_start_logs_warning(self, monkeypatch, caplog):
        monkeypatch.setattr(sys, "platform", "linux")
        capture = create_input_capture()

        with caplog.at_level(logging.WARNING):
            capture.start()

        assert "InputCapture is not supported on this platform" in caplog.text

    def test_running_is_false(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        capture = create_input_capture()

        assert not capture.running

    def test_set_listener_does_not_crash(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        capture = create_input_capture()

        capture.set_listener(lambda e: "pass_through")


class TestNullHotkeyCapture:
    def test_start_logs_warning(self, monkeypatch, caplog):
        monkeypatch.setattr(sys, "platform", "linux")
        capture = create_hotkey_capture()

        with caplog.at_level(logging.WARNING):
            capture.start()

        assert "HotkeyCapture is not supported on this platform" in caplog.text

    def test_running_is_false(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        capture = create_hotkey_capture()

        assert not capture.running

    def test_set_handler_does_not_crash(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        capture = create_hotkey_capture()

        capture.set_handler(lambda: None)
```

- [ ] **Step 2: Run tests, expect FAIL (module not found)**

```bash
PYTHONPATH=src python -m pytest tests/unit/test_bootstrap_platform.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'bootstrap.platform'`

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_bootstrap_platform.py
git commit -m "test: add bootstrap platform unit tests"
```

---

### Task 5: Implement `src/bootstrap/platform.py`

**Files:**
- Create: `src/bootstrap/platform.py`

- [ ] **Step 1: Write `src/bootstrap/platform.py`**

```python
import importlib
import logging
import sys
from typing import Any

from adapters.inputs.base import HotkeyCapture, InputCapture
from adapters.outputs.drivers.pyttsx3 import Pyttsx3SpeechOutput
from application.output_scheduler import OutputScheduler
from application.services import ClipboardService
from application.speech_backends import SpeechBackendOption

_logger = logging.getLogger(__name__)

# --- lazy import cache variables ---
_WindowsKeyboardCapture: Any = None
_WindowsHotkeyCapture: Any = None
_WindowsClipboardService: Any = None
_NvdaControllerSpeechOutput: Any = None
_AccessibilityPermissions: Any = None
_MacOSEventTapManager: Any = None
_MacOSEventTapBackend: Any = None
_MacOSKeyboardCapture: Any = None
_MacOSHotkeyCapture: Any = None
_macos_event_tap_manager_instance: Any = None


# --- null / fallback implementations ---

class _NullInputCapture:
    @property
    def running(self) -> bool:
        return False

    def set_listener(self, listener: Any) -> None:
        del listener

    def start(self) -> None:
        _logger.warning("InputCapture is not supported on this platform")

    def stop(self) -> None:
        pass


class _NullHotkeyCapture:
    @property
    def running(self) -> bool:
        return False

    def set_handler(self, handler: Any) -> None:
        del handler

    def start(self) -> None:
        _logger.warning("HotkeyCapture is not supported on this platform")

    def stop(self) -> None:
        pass


class _UnsupportedClipboardService:
    supported = False

    def set_text(self, text: str) -> None:
        del text

    def get_text(self) -> str:
        return ""


class _UnavailableMacOSPermissions:
    def is_trusted(self, *, prompt: bool = False) -> bool:
        del prompt
        raise RuntimeError("macOS accessibility permission wiring is unavailable")

    def has_listen_event_access(self, *, prompt: bool = False) -> bool:
        del prompt
        raise RuntimeError("macOS input monitoring permission wiring is unavailable")


# --- Windows lazy helpers ---

def _get_windows_keyboard_capture_class() -> Any:
    global _WindowsKeyboardCapture
    if _WindowsKeyboardCapture is None:
        from adapters.windows.keyboard_hook import WindowsKeyboardCapture as Capture
        _WindowsKeyboardCapture = Capture
    return _WindowsKeyboardCapture


def _get_windows_hotkey_capture_class() -> Any:
    global _WindowsHotkeyCapture
    if _WindowsHotkeyCapture is None:
        from adapters.windows.hotkey import WindowsHotkeyCapture as Capture
        _WindowsHotkeyCapture = Capture
    return _WindowsHotkeyCapture


def _get_windows_clipboard_service_class() -> Any:
    global _WindowsClipboardService
    if _WindowsClipboardService is None:
        from adapters.windows.clipboard import WindowsClipboardService as Service
        _WindowsClipboardService = Service
    return _WindowsClipboardService


def _get_nvda_controller_speech_output_class() -> Any:
    global _NvdaControllerSpeechOutput
    if _NvdaControllerSpeechOutput is None:
        from adapters.windows.nvda_controller import NvdaControllerSpeechOutput as Output
        _NvdaControllerSpeechOutput = Output
    return _NvdaControllerSpeechOutput


# --- macOS lazy helpers ---

def _get_macos_permissions_type() -> Any:
    global _AccessibilityPermissions
    if _AccessibilityPermissions is None:
        module = importlib.import_module("adapters.macos.permissions")
        _AccessibilityPermissions = module.AccessibilityPermissions
    return _AccessibilityPermissions


def _load_macos_permissions() -> Any:
    permissions_type = _get_macos_permissions_type()
    load_default = getattr(permissions_type, "load_default", None)
    if callable(load_default):
        return load_default()
    return _UnavailableMacOSPermissions()


def _load_macos_event_tap_backend() -> Any:
    global _MacOSEventTapBackend
    _load_macos_input_components()
    return _MacOSEventTapBackend()


def _load_macos_input_components() -> None:
    global _MacOSEventTapManager
    global _MacOSEventTapBackend
    global _MacOSKeyboardCapture
    global _MacOSHotkeyCapture
    if (
        _MacOSEventTapManager is not None
        and _MacOSEventTapBackend is not None
        and _MacOSKeyboardCapture is not None
        and _MacOSHotkeyCapture is not None
    ):
        return
    try:
        event_tap = importlib.import_module("adapters.macos.event_tap")
        hotkey = importlib.import_module("adapters.macos.hotkey")
        keyboard_hook = importlib.import_module("adapters.macos.keyboard_hook")
    except ImportError as error:
        raise RuntimeError("macOS input capture dependencies are unavailable") from error
    _MacOSEventTapManager = event_tap.MacOSEventTapManager
    _MacOSEventTapBackend = event_tap.QuartzEventTapBackend
    _MacOSKeyboardCapture = keyboard_hook.MacOSKeyboardCapture
    _MacOSHotkeyCapture = hotkey.MacOSHotkeyCapture


def _ensure_macos_event_tap_manager() -> Any:
    global _macos_event_tap_manager_instance
    if _macos_event_tap_manager_instance is None:
        _load_macos_input_components()
        _macos_event_tap_manager_instance = _MacOSEventTapManager(
            permissions=_load_macos_permissions(),
            backend=_load_macos_event_tap_backend(),
        )
    return _macos_event_tap_manager_instance


# --- public factory functions ---

def create_input_capture() -> InputCapture:
    if sys.platform == "darwin":
        return _MacOSKeyboardCapture(manager=_ensure_macos_event_tap_manager())
    if sys.platform == "win32":
        return _get_windows_keyboard_capture_class()()
    return _NullInputCapture()


def create_hotkey_capture() -> HotkeyCapture:
    if sys.platform == "darwin":
        return _MacOSHotkeyCapture(manager=_ensure_macos_event_tap_manager())
    if sys.platform == "win32":
        return _get_windows_hotkey_capture_class()()
    return _NullHotkeyCapture()


def create_clipboard_service() -> ClipboardService:
    if sys.platform == "win32":
        return _get_windows_clipboard_service_class()()
    return _UnsupportedClipboardService()


def default_speech_backend_options(
    scheduler: OutputScheduler,
) -> tuple[SpeechBackendOption, ...]:
    options = [
        SpeechBackendOption(
            backend_id="pyttsx3",
            label="pyttsx3",
            factory=lambda: Pyttsx3SpeechOutput.load_default(scheduler=scheduler),
        ),
    ]
    if sys.platform == "win32":
        options.insert(
            0,
            SpeechBackendOption(
                backend_id="nvda_controller",
                label="NVDA Controller",
                factory=lambda: _get_nvda_controller_speech_output_class().load_default(
                    scheduler=scheduler
                ),
            ),
        )
    return tuple(options)


def default_speech_backend_id() -> str:
    return "nvda_controller" if sys.platform == "win32" else "pyttsx3"
```

- [ ] **Step 2: Run platform tests, expect PASS**

```bash
PYTHONPATH=src python -m pytest tests/unit/test_bootstrap_platform.py -v
```

Expected: all tests PASS

- [ ] **Step 3: Commit**

```bash
git add src/bootstrap/platform.py
git commit -m "feat: add bootstrap/platform.py with adapter factory functions"
```

---

### Task 6: Refactor `src/apps/nvda_remote/main.py`

**Files:**
- Modify: `src/apps/nvda_remote/main.py`

- [ ] **Step 1: Rewrite `nvda_remote/main.py` to use bootstrap**

Replace the entire file content with:

```python
from dataclasses import dataclass
import logging
from typing import Any

from adapters.inputs.base import HotkeyCapture, InputCapture
from application.config import SpeechBackendConfigStore
from application.keyboard import KeyboardInputService
from application.output_scheduler import OutputScheduler
from application.output_service import QueuedOutputService
from application.services import ClipboardService
from application.speech_service import SpeechService
from apps.nvda_remote.service import NvdaRemoteAppService
from bootstrap.platform import (
    create_input_capture,
    create_hotkey_capture,
    create_clipboard_service,
    default_speech_backend_options,
    default_speech_backend_id,
)
from bootstrap.runtime import configure_logging, default_config_path
from interop.protocol.serializer import JSONSerializer
from interop.protocol.transport.relay import RelayTransport
from ui.nvda_remote.app import NvdaRemoteApp


@dataclass(frozen=True)
class NvdaRemoteRuntime:
    config_store: SpeechBackendConfigStore
    transport: RelayTransport
    input_capture: InputCapture
    hotkey_capture: HotkeyCapture
    clipboard: ClipboardService
    output_scheduler: OutputScheduler
    speech_service: SpeechService
    output_service: QueuedOutputService
    input_service: KeyboardInputService
    app_service: NvdaRemoteAppService
    app: Any


def build_runtime() -> NvdaRemoteRuntime:
    config_store = SpeechBackendConfigStore(default_config_path())
    output_scheduler = OutputScheduler()
    backend_options = default_speech_backend_options(output_scheduler)
    default_bid = default_speech_backend_id()
    selected_backend_id = config_store.load_backend_id(
        default_backend_id=default_bid
    )
    try:
        speech_service = SpeechService(
            backend_options=backend_options,
            selected_backend_id=selected_backend_id,
        )
    except ValueError:
        logging.getLogger(__name__).warning(
            "Unknown configured speech backend %r; falling back to %s",
            selected_backend_id,
            default_bid,
        )
        speech_service = SpeechService(
            backend_options=backend_options,
            selected_backend_id=default_bid,
        )
        config_store.save_backend_id(default_bid)

    transport = RelayTransport(JSONSerializer())
    input_capture = create_input_capture()
    hotkey_capture = create_hotkey_capture()
    clipboard = create_clipboard_service()
    app_service = NvdaRemoteAppService(
        transport=transport,
        input_capture=input_capture,
        hotkey_capture=hotkey_capture,
        clipboard=clipboard,
        speech=QueuedOutputService(speech=speech_service, scheduler=output_scheduler),
        on_speech_backend_changed=config_store.save_backend_id,
        main_thread_dispatch=getattr(NvdaRemoteApp, "dispatch", None),
    )
    input_service = KeyboardInputService(input_capture, app_service)
    app_service.bind()
    input_service.bind()
    app = NvdaRemoteApp(controller=app_service)
    return NvdaRemoteRuntime(
        config_store=config_store,
        transport=transport,
        input_capture=input_capture,
        hotkey_capture=hotkey_capture,
        clipboard=clipboard,
        output_scheduler=output_scheduler,
        speech_service=speech_service,
        output_service=app_service.speech,
        input_service=input_service,
        app_service=app_service,
        app=app,
    )


def main() -> int:
    try:
        configure_logging(app_name="nvda-remote-client")
    except OSError:
        if not logging.getLogger().handlers:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            )
        logging.getLogger(__name__).warning(
            "Logging initialization failed; continuing without file logging",
            exc_info=True,
        )
    runtime = build_runtime()
    return runtime.app.MainLoop()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run full test suite**

```bash
PYTHONPATH=src python -m pytest tests/unit tests/integration -v
```

Expected: all tests PASS

- [ ] **Step 3: Commit**

```bash
git add src/apps/nvda_remote/main.py
git commit -m "refactor: nvda_remote main.py uses bootstrap layer"
```

---

### Task 7: Refactor `src/apps/key_echo/main.py`

**Files:**
- Modify: `src/apps/key_echo/main.py`

- [ ] **Step 1: Rewrite `key_echo/main.py` to use bootstrap**

Replace the entire file content with:

```python
from dataclasses import dataclass
from typing import Any

from application.keyboard import KeyboardInputService
from application.output_capabilities import OutputCapabilities
from application.output_scheduler import OutputScheduler
from application.output_service import QueuedOutputService
from application.speech_service import SpeechService
from apps.key_echo.service import KeyEchoAppService
from bootstrap.platform import (
    create_input_capture,
    default_speech_backend_options,
)


@dataclass(frozen=True)
class KeyEchoRuntime:
    capture: Any
    output_scheduler: OutputScheduler
    speech_service: SpeechService
    output_service: QueuedOutputService
    input_service: KeyboardInputService
    app_service: KeyEchoAppService
    app: Any


def build_runtime() -> KeyEchoRuntime:
    from ui.echo.app import EchoApp

    capture = create_input_capture()
    output_scheduler = OutputScheduler()
    speech_service = SpeechService(
        backend_options=default_speech_backend_options(output_scheduler),
        selected_backend_id="pyttsx3",
    )
    output_service = QueuedOutputService(
        speech=speech_service,
        scheduler=output_scheduler,
    )
    app_service = KeyEchoAppService(
        outputs=OutputCapabilities(speech=output_service),
    )
    input_service = KeyboardInputService(capture, app_service)
    input_service.bind()
    app_service.attach_input_service(input_service)
    app = EchoApp(controller=app_service)
    return KeyEchoRuntime(
        capture=capture,
        output_scheduler=output_scheduler,
        speech_service=speech_service,
        output_service=output_service,
        input_service=input_service,
        app_service=app_service,
        app=app,
    )


def main() -> int:
    runtime = build_runtime()
    return runtime.app.MainLoop()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run full test suite**

```bash
PYTHONPATH=src python -m pytest tests/unit tests/integration -v
```

Expected: all tests PASS

- [ ] **Step 3: Commit**

```bash
git add src/apps/key_echo/main.py
git commit -m "refactor: key_echo main.py uses bootstrap layer"
```

---

### Task 8: Final verification

- [ ] **Step 1: Run full test suite one final time**

```bash
PYTHONPATH=src python -m pytest tests/unit tests/integration -v
```

Expected: all tests PASS

- [ ] **Step 2: Verify neither main.py contains platform-lazy-import patterns**

```bash
grep -n "sys.platform\|importlib\|_get_windows\|_get_nvda\|_get_macos\|_load_macos\|_build_macos\|_build_input\|_build_clipboard" src/apps/nvda_remote/main.py src/apps/key_echo/main.py || echo "CLEAN: no platform/lazy-import helpers remain in main.py files"
```

Expected: `CLEAN` — no matching lines in either main.py

- [ ] **Step 3: Commit**

```bash
git add src/apps/nvda_remote/main.py src/apps/key_echo/main.py
git commit -m "chore: verify clean bootstrap extraction"
```
