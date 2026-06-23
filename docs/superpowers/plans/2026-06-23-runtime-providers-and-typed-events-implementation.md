# Runtime Providers And Typed Events Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract shared runtime provider/builders from app entrypoints, then migrate all three apps to typed UI-facing events.

**Architecture:** This plan is split into two reviewable milestones. M1 introduces focused bootstrap provider/builders and keeps app behavior unchanged. M2 builds on that cleaner boundary and replaces dict-first status listeners with typed dataclass events, with shared events in `application/events.py` and app-domain events in each app package.

**Tech Stack:** Python 3.11+, dataclasses, pytest, wxPython app shell, existing `src` package layout.

---

## Milestone Boundaries

M1 can be implemented, tested, committed, and merged independently. M2 should start only after M1 is green because it relies on the entrypoints being thinner and easier to reason about.

M1 target commit series:

- `test: cover bootstrap platform provider`
- `refactor: add runtime output builder`
- `refactor: centralize app runtime wiring`
- `refactor: use shared runtime builders in app entrypoints`

M2 target commit series:

- `feat: add typed application events`
- `feat: add app typed events`
- `refactor: migrate key echo typed events`
- `refactor: migrate access8graph typed events`
- `refactor: migrate nvda remote typed events`
- `refactor: migrate UI status consumers to typed events`

## File Structure

Create or modify these files in M1:

- Modify: `src/bootstrap/platform.py`
  - Keep existing factory functions.
  - Add `PlatformProvider` and `PlatformServices` as a provider-facing layer over the existing factories.
- Create: `src/bootstrap/output.py`
  - Own `OutputServices` and `build_output_services()`.
  - Assemble `Scheduler`, `SpeechService`, `QueuedService`, and `Capabilities`.
- Create: `src/bootstrap/app_runtime.py`
  - Own `AppRuntimeParts` and `build_app_runtime_parts()`.
  - Build common input/hotkey/platform/output parts for app entrypoints.
- Modify: `src/apps/key_echo/main.py`
  - Replace local shared runtime assembly with `build_app_runtime_parts()`.
- Modify: `src/apps/access8graph/main.py`
  - Replace local shared runtime assembly with `build_app_runtime_parts()`.
- Modify: `src/apps/nvda_remote/main.py`
  - Replace local shared runtime assembly with `build_app_runtime_parts()`.
- Modify: `tests/unit/test_bootstrap_platform.py`
  - Add provider tests without deleting existing factory tests.
- Create: `tests/unit/test_bootstrap_output.py`
  - Cover output service assembly and fallback on unknown backend.
- Create: `tests/unit/test_bootstrap_app_runtime.py`
  - Cover common app runtime part assembly.
- Modify: existing app runtime tests touched by imports or runtime shape:
  - `tests/unit/test_key_echo_app_service.py`
  - `tests/unit/test_access8graph_app_service.py`
  - `tests/unit/test_nvda_remote_app_service.py`
  - `tests/unit/test_app_wx.py`

Create or modify these files in M2:

- Modify: `src/application/events.py`
  - Replace generic dict wrapper as the primary event model.
  - Keep `StatusEvent.from_payload()` only as a transitional compatibility helper if existing router tests still need it.
- Create: `src/apps/key_echo/events.py`
  - Define Key Echo app-domain events.
- Create: `src/apps/access8graph/events.py`
  - Define Access8Graph app-domain events.
- Create: `src/apps/nvda_remote/events.py`
  - Define NVDA Remote app-domain events.
- Modify: `src/apps/shared/mode_manager.py`
  - Emit typed mode events instead of dict payloads.
- Modify: app services:
  - `src/apps/key_echo/service.py`
  - `src/apps/access8graph/service.py`
  - `src/apps/nvda_remote/service.py`
- Modify: use cases that currently emit dict statuses:
  - `src/apps/key_echo/use_cases/echo_control.py`
  - `src/apps/nvda_remote/use_cases/control_mode.py`
- Modify: UI consumers:
  - `src/ui/echo/main_frame.py`
  - `src/ui/access8graph/main_frame.py`
  - `src/ui/nvda_remote/main_frame.py`
- Create: `tests/unit/test_application_events.py`
- Create: `tests/unit/test_app_events.py`
- Modify: event/status tests:
  - `tests/unit/test_key_echo_app_service.py`
  - `tests/unit/test_access8graph_app_service.py`
  - `tests/unit/test_nvda_remote_app_service.py`
  - `tests/unit/test_key_echo_use_cases.py`
  - `tests/unit/test_nvda_remote_use_cases.py`
  - `tests/unit/test_mode_manager.py`
  - `tests/unit/test_app_wx.py`
  - `tests/unit/test_access8graph_ui.py`

---

## M1: Runtime Provider Extraction

### Task 1: Add `PlatformProvider` Over Existing Platform Factories

**Files:**
- Modify: `tests/unit/test_bootstrap_platform.py`
- Modify: `src/bootstrap/platform.py`

- [ ] **Step 1: Write failing provider tests**

Append these tests to `tests/unit/test_bootstrap_platform.py`:

```python
class TestPlatformProvider:
    def test_provider_builds_common_platform_services_on_unsupported_platform(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        provider = _bp.PlatformProvider()

        services = provider.build_services(hotkey_usage=HID.ENTER)

        assert not services.input_capture.running
        assert not services.hotkey_capture.running
        assert services.clipboard.get_text() == ""
        assert services.tone_output is not None

    def test_provider_exposes_default_speech_backend_id(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        provider = _bp.PlatformProvider()

        assert provider.default_speech_backend_id() == "pyttsx3"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/unit/test_bootstrap_platform.py::TestPlatformProvider -v
```

Expected: fail with `AttributeError: module 'bootstrap.platform' has no attribute 'PlatformProvider'`.

- [ ] **Step 3: Add provider dataclasses and methods**

Add this near the public factory functions in `src/bootstrap/platform.py`:

```python
from dataclasses import dataclass
```

Add these types before `create_input_capture()`:

```python
@dataclass(frozen=True)
class PlatformServices:
    input_capture: InputCapture
    hotkey_capture: HotkeyCapture
    clipboard: ClipboardService
    tone_output: DefaultToneOutput


class PlatformProvider:
    def create_input_capture(self) -> InputCapture:
        return create_input_capture()

    def create_hotkey_capture(self, usage: int = _DEFAULT_HOTKEY_USAGE) -> HotkeyCapture:
        return create_hotkey_capture(usage)

    def create_clipboard_service(self) -> ClipboardService:
        return create_clipboard_service()

    def create_tone_output(self) -> DefaultToneOutput:
        return create_tone_output()

    def default_speech_backend_options(
        self,
        scheduler: Scheduler,
    ) -> tuple[SpeechBackendOption, ...]:
        return default_speech_backend_options(scheduler)

    def default_speech_backend_id(self) -> str:
        return default_speech_backend_id()

    def build_services(self, *, hotkey_usage: int = _DEFAULT_HOTKEY_USAGE) -> PlatformServices:
        return PlatformServices(
            input_capture=self.create_input_capture(),
            hotkey_capture=self.create_hotkey_capture(hotkey_usage),
            clipboard=self.create_clipboard_service(),
            tone_output=self.create_tone_output(),
        )
```

- [ ] **Step 4: Run provider tests**

Run:

```bash
pytest tests/unit/test_bootstrap_platform.py::TestPlatformProvider -v
```

Expected: pass.

- [ ] **Step 5: Run full platform tests**

Run:

```bash
pytest tests/unit/test_bootstrap_platform.py -v
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add src/bootstrap/platform.py tests/unit/test_bootstrap_platform.py
git commit -m "test: cover bootstrap platform provider"
```

### Task 2: Add Output Service Builder

**Files:**
- Create: `tests/unit/test_bootstrap_output.py`
- Create: `src/bootstrap/output.py`

- [ ] **Step 1: Write failing output builder tests**

Create `tests/unit/test_bootstrap_output.py`:

```python
from application.output import Scheduler
from application.output.speech import SpeechBackendOption
from bootstrap.output import build_output_services


class FakeSpeechOutput:
    def __init__(self):
        self.spoken = []

    def speak(self, text: str) -> None:
        self.spoken.append(text)

    def cancel(self) -> None:
        self.spoken.clear()


def _backend_options(scheduler: Scheduler) -> tuple[SpeechBackendOption, ...]:
    assert isinstance(scheduler, Scheduler)
    return (
        SpeechBackendOption(
            backend_id="default",
            label="Default",
            factory=FakeSpeechOutput,
        ),
    )


def test_build_output_services_wires_scheduler_speech_speaker_and_capabilities():
    services = build_output_services(
        backend_options_factory=_backend_options,
        selected_backend_id="default",
    )
    try:
        assert isinstance(services.scheduler, Scheduler)
        assert services.speech.selected_backend_id == "default"
        assert services.capabilities.speech is services.speaker
        assert services.capabilities.tone is None
    finally:
        services.scheduler.shutdown()


def test_build_output_services_includes_tone_capability():
    tone_output = object()

    services = build_output_services(
        backend_options_factory=_backend_options,
        selected_backend_id="default",
        tone_output=tone_output,
    )
    try:
        assert services.capabilities.tone is tone_output
    finally:
        services.scheduler.shutdown()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/unit/test_bootstrap_output.py -v
```

Expected: fail with `ModuleNotFoundError: No module named 'bootstrap.output'`.

- [ ] **Step 3: Add output builder implementation**

Create `src/bootstrap/output.py`:

```python
from collections.abc import Callable
from dataclasses import dataclass
import logging

from application.output import Capabilities
from application.output import QueuedService
from application.output import Scheduler
from application.output.speech import SpeechBackendOption
from application.output.speech import SpeechService

_logger = logging.getLogger(__name__)

SpeechBackendOptionsFactory = Callable[[Scheduler], tuple[SpeechBackendOption, ...]]


@dataclass(frozen=True)
class OutputServices:
    scheduler: Scheduler
    speech: SpeechService
    speaker: QueuedService
    capabilities: Capabilities


def build_output_services(
    *,
    backend_options_factory: SpeechBackendOptionsFactory,
    selected_backend_id: str,
    fallback_backend_id: str | None = None,
    tone_output: object | None = None,
    on_backend_fallback: Callable[[str], None] | None = None,
) -> OutputServices:
    scheduler = Scheduler()
    backend_options = backend_options_factory(scheduler)
    fallback_id = fallback_backend_id or selected_backend_id
    try:
        speech = SpeechService(
            backend_options=backend_options,
            selected_backend_id=selected_backend_id,
            scheduler=scheduler,
        )
    except ValueError:
        _logger.warning(
            "Unknown configured speech backend %r; falling back to %s",
            selected_backend_id,
            fallback_id,
        )
        speech = SpeechService(
            backend_options=backend_options,
            selected_backend_id=fallback_id,
            scheduler=scheduler,
        )
        if on_backend_fallback is not None:
            on_backend_fallback(fallback_id)
    speaker = QueuedService(speech=speech)
    return OutputServices(
        scheduler=scheduler,
        speech=speech,
        speaker=speaker,
        capabilities=Capabilities(speech=speaker, tone=tone_output),
    )
```

- [ ] **Step 4: Run output builder tests**

Run:

```bash
pytest tests/unit/test_bootstrap_output.py -v
```

Expected: pass.

- [ ] **Step 5: Add unknown backend fallback test**

Append to `tests/unit/test_bootstrap_output.py`:

```python
def test_build_output_services_falls_back_and_persists_fallback_backend():
    saved = []

    services = build_output_services(
        backend_options_factory=_backend_options,
        selected_backend_id="missing",
        fallback_backend_id="default",
        on_backend_fallback=saved.append,
    )
    try:
        assert services.speech.selected_backend_id == "default"
        assert saved == ["default"]
    finally:
        services.scheduler.shutdown()
```

- [ ] **Step 6: Run output builder tests**

Run:

```bash
pytest tests/unit/test_bootstrap_output.py -v
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add src/bootstrap/output.py tests/unit/test_bootstrap_output.py
git commit -m "refactor: add runtime output builder"
```

### Task 3: Add Common App Runtime Parts Builder

**Files:**
- Create: `tests/unit/test_bootstrap_app_runtime.py`
- Create: `src/bootstrap/app_runtime.py`

- [ ] **Step 1: Write failing common runtime tests**

Create `tests/unit/test_bootstrap_app_runtime.py`:

```python
from dataclasses import dataclass

from application.output import Scheduler
from application.output.speech import SpeechBackendOption
from bootstrap.app_runtime import build_app_runtime_parts
from bootstrap.platform import PlatformServices


class FakeCapture:
    running = False

    def set_listener(self, listener):
        self.listener = listener

    def start(self):
        self.running = True

    def stop(self):
        self.running = False


class FakeHotkeyCapture(FakeCapture):
    def set_handler(self, handler):
        self.handler = handler


class FakeSpeechOutput:
    def speak(self, text: str) -> None:
        self.text = text

    def cancel(self) -> None:
        self.text = ""


@dataclass
class FakeProvider:
    services: PlatformServices

    def build_services(self, *, hotkey_usage: int) -> PlatformServices:
        self.hotkey_usage = hotkey_usage
        return self.services

    def default_speech_backend_options(
        self,
        scheduler: Scheduler,
    ) -> tuple[SpeechBackendOption, ...]:
        return (
            SpeechBackendOption(
                backend_id="default",
                label="Default",
                factory=FakeSpeechOutput,
            ),
        )

    def default_speech_backend_id(self) -> str:
        return "default"


def test_build_app_runtime_parts_wires_platform_and_output_services():
    input_capture = FakeCapture()
    hotkey_capture = FakeHotkeyCapture()
    clipboard = object()
    tone_output = object()
    provider = FakeProvider(
        PlatformServices(
            input_capture=input_capture,
            hotkey_capture=hotkey_capture,
            clipboard=clipboard,
            tone_output=tone_output,
        )
    )

    parts = build_app_runtime_parts(provider=provider, hotkey_usage=0x28)
    try:
        assert provider.hotkey_usage == 0x28
        assert parts.input_capture is input_capture
        assert parts.hotkey_capture is hotkey_capture
        assert parts.clipboard is clipboard
        assert parts.tone_output is tone_output
        assert parts.output.capabilities.speech is parts.output.speaker
        assert parts.output.capabilities.tone is tone_output
    finally:
        parts.output.scheduler.shutdown()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/unit/test_bootstrap_app_runtime.py -v
```

Expected: fail with `ModuleNotFoundError: No module named 'bootstrap.app_runtime'`.

- [ ] **Step 3: Add common runtime builder implementation**

Create `src/bootstrap/app_runtime.py`:

```python
from dataclasses import dataclass

from adapters.inputs.base import HotkeyCapture
from adapters.inputs.base import InputCapture
from application.output import ClipboardService
from bootstrap.output import OutputServices
from bootstrap.output import build_output_services
from bootstrap.platform import PlatformProvider


@dataclass(frozen=True)
class AppRuntimeParts:
    input_capture: InputCapture
    hotkey_capture: HotkeyCapture
    clipboard: ClipboardService
    tone_output: object
    output: OutputServices


def build_app_runtime_parts(
    *,
    provider: PlatformProvider | None = None,
    hotkey_usage: int,
    selected_backend_id: str | None = None,
    fallback_backend_id: str | None = None,
    on_backend_fallback=None,
    include_tone: bool = True,
) -> AppRuntimeParts:
    runtime_provider = provider or PlatformProvider()
    platform_services = runtime_provider.build_services(hotkey_usage=hotkey_usage)
    default_backend_id = runtime_provider.default_speech_backend_id()
    backend_id = selected_backend_id or default_backend_id
    fallback_id = fallback_backend_id or default_backend_id
    tone_output = platform_services.tone_output if include_tone else None
    output = build_output_services(
        backend_options_factory=runtime_provider.default_speech_backend_options,
        selected_backend_id=backend_id,
        fallback_backend_id=fallback_id,
        tone_output=tone_output,
        on_backend_fallback=on_backend_fallback,
    )
    return AppRuntimeParts(
        input_capture=platform_services.input_capture,
        hotkey_capture=platform_services.hotkey_capture,
        clipboard=platform_services.clipboard,
        tone_output=platform_services.tone_output,
        output=output,
    )
```

- [ ] **Step 4: Run common runtime tests**

Run:

```bash
pytest tests/unit/test_bootstrap_app_runtime.py -v
```

Expected: pass.

- [ ] **Step 5: Add no-tone test for Key Echo runtime shape**

Append to `tests/unit/test_bootstrap_app_runtime.py`:

```python
def test_build_app_runtime_parts_can_exclude_tone_capability():
    provider = FakeProvider(
        PlatformServices(
            input_capture=FakeCapture(),
            hotkey_capture=FakeHotkeyCapture(),
            clipboard=object(),
            tone_output=object(),
        )
    )

    parts = build_app_runtime_parts(
        provider=provider,
        hotkey_usage=0x28,
        include_tone=False,
    )
    try:
        assert parts.output.capabilities.tone is None
        assert parts.tone_output is provider.services.tone_output
    finally:
        parts.output.scheduler.shutdown()
```

- [ ] **Step 6: Run common runtime tests**

Run:

```bash
pytest tests/unit/test_bootstrap_app_runtime.py -v
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add src/bootstrap/app_runtime.py tests/unit/test_bootstrap_app_runtime.py
git commit -m "refactor: centralize app runtime wiring"
```

### Task 4: Refactor Key Echo Entrypoint To Use Runtime Parts

**Files:**
- Modify: `src/apps/key_echo/main.py`
- Verify: `tests/unit/test_app_wx.py`

- [ ] **Step 1: Run current Key Echo runtime tests as baseline**

Run:

```bash
pytest tests/unit/test_app_wx.py -k "echo or key_echo" -v
```

Expected: pass before edits.

- [ ] **Step 2: Replace local output/platform assembly in Key Echo main**

In `src/apps/key_echo/main.py`, remove these imports:

```python
from application.output import Capabilities
from application.output import Scheduler
from application.output import QueuedService
from application.output.speech import SpeechService
from bootstrap.platform import (
    create_hotkey_capture,
    create_input_capture,
    default_speech_backend_options,
)
```

Add:

```python
from application.output import Scheduler
from application.output import QueuedService
from application.output.speech import SpeechService
from bootstrap.app_runtime import build_app_runtime_parts
```

Replace the shared assembly block inside `build_runtime()`:

```python
    input_capture = create_input_capture()
    hotkey_capture = create_hotkey_capture(KeyEchoAppService.enter_usage)
    scheduler = Scheduler()
    speech = SpeechService(
        backend_options=default_speech_backend_options(scheduler),
        selected_backend_id="pyttsx3",
        scheduler=scheduler,
    )
    speaker = QueuedService(
        speech=speech,
    )
```

with:

```python
    parts = build_app_runtime_parts(
        hotkey_usage=KeyEchoAppService.enter_usage,
        selected_backend_id="pyttsx3",
        fallback_backend_id="pyttsx3",
        include_tone=False,
    )
    input_capture = parts.input_capture
    hotkey_capture = parts.hotkey_capture
    scheduler = parts.output.scheduler
    speech = parts.output.speech
    speaker = parts.output.speaker
```

Replace:

```python
        capabilities=Capabilities(speech=speaker),
```

with:

```python
        capabilities=parts.output.capabilities,
```

- [ ] **Step 3: Run Key Echo runtime tests**

Run:

```bash
pytest tests/unit/test_app_wx.py -k "echo or key_echo" -v
```

Expected: pass.

- [ ] **Step 4: Commit**

```bash
git add src/apps/key_echo/main.py tests/unit/test_app_wx.py
git commit -m "refactor: use shared runtime builder in key echo"
```

### Task 5: Refactor Access8Graph Entrypoint To Use Runtime Parts

**Files:**
- Modify: `src/apps/access8graph/main.py`
- Verify: `tests/unit/test_app_wx.py`

- [ ] **Step 1: Run current Access8Graph runtime tests as baseline**

Run:

```bash
pytest tests/unit/test_app_wx.py -k "access8graph" -v
```

Expected: pass before edits.

- [ ] **Step 2: Replace local output/platform assembly in Access8Graph main**

In `src/apps/access8graph/main.py`, remove these imports:

```python
from application.output import Capabilities
from bootstrap.platform import (
    create_hotkey_capture,
    create_input_capture,
    create_tone_output,
    default_speech_backend_id,
    default_speech_backend_options,
)
```

Add:

```python
from bootstrap.app_runtime import build_app_runtime_parts
```

Replace the shared assembly block inside `build_runtime()`:

```python
    input_capture = create_input_capture()
    hotkey_capture = create_hotkey_capture(Access8GraphAppService.enter_usage)
    tone_output = create_tone_output()
    scheduler = Scheduler()
    speech = SpeechService(
        backend_options=default_speech_backend_options(scheduler),
        selected_backend_id=default_speech_backend_id(),
        scheduler=scheduler,
    )
    speaker = QueuedService(speech=speech)
```

with:

```python
    parts = build_app_runtime_parts(
        hotkey_usage=Access8GraphAppService.enter_usage,
    )
    input_capture = parts.input_capture
    hotkey_capture = parts.hotkey_capture
    tone_output = parts.tone_output
    scheduler = parts.output.scheduler
    speech = parts.output.speech
    speaker = parts.output.speaker
```

Replace:

```python
        capabilities=Capabilities(speech=speaker, tone=tone_output),
```

with:

```python
        capabilities=parts.output.capabilities,
```

- [ ] **Step 3: Run Access8Graph runtime tests**

Run:

```bash
pytest tests/unit/test_app_wx.py -k "access8graph" -v
```

Expected: pass.

- [ ] **Step 4: Commit**

```bash
git add src/apps/access8graph/main.py tests/unit/test_app_wx.py
git commit -m "refactor: use shared runtime builder in access8graph"
```

### Task 6: Refactor NVDA Remote Entrypoint To Use Runtime Parts

**Files:**
- Modify: `src/apps/nvda_remote/main.py`
- Verify: `tests/unit/test_app_wx.py`

- [ ] **Step 1: Run current NVDA Remote runtime tests as baseline**

Run:

```bash
pytest tests/unit/test_app_wx.py -k "nvda_remote or remote" -v
```

Expected: pass before edits.

- [ ] **Step 2: Replace local output/platform assembly in NVDA Remote main**

In `src/apps/nvda_remote/main.py`, remove these imports:

```python
from application.output import Capabilities
from bootstrap.platform import (
    create_input_capture,
    create_hotkey_capture,
    create_clipboard_service,
    create_tone_output,
    default_speech_backend_options,
    default_speech_backend_id,
)
```

Add:

```python
from bootstrap.app_runtime import build_app_runtime_parts
from bootstrap.platform import PlatformProvider
```

Replace this block inside `build_runtime()`:

```python
    scheduler = Scheduler()
    backend_options = default_speech_backend_options(scheduler)
    default_bid = default_speech_backend_id()
    selected_backend_id = config_store.load_backend_id(
        default_backend_id=default_bid
    )
    try:
        speech = SpeechService(
            backend_options=backend_options,
            selected_backend_id=selected_backend_id,
            scheduler=scheduler,
        )
    except ValueError:
        logging.getLogger(__name__).warning(
            "Unknown configured speech backend %r; falling back to %s",
            selected_backend_id,
            default_bid,
        )
        speech = SpeechService(
            backend_options=backend_options,
            selected_backend_id=default_bid,
            scheduler=scheduler,
        )
        config_store.save_backend_id(default_bid)
```

with:

```python
    provider = PlatformProvider()
    default_bid = provider.default_speech_backend_id()
    selected_backend_id = config_store.load_backend_id(default_backend_id=default_bid)
    parts = build_app_runtime_parts(
        provider=provider,
        hotkey_usage=NvdaRemoteAppService.enter_usage,
        selected_backend_id=selected_backend_id,
        fallback_backend_id=default_bid,
        on_backend_fallback=config_store.save_backend_id,
    )
    scheduler = parts.output.scheduler
    speech = parts.output.speech
```

Replace this block:

```python
    input_capture = create_input_capture()
    hotkey_capture = create_hotkey_capture(NvdaRemoteAppService.enter_usage)
    clipboard = create_clipboard_service()
    tone_output = create_tone_output()
    speaker = QueuedService(speech=speech)
```

with:

```python
    input_capture = parts.input_capture
    hotkey_capture = parts.hotkey_capture
    clipboard = parts.clipboard
    tone_output = parts.tone_output
    speaker = parts.output.speaker
```

Replace:

```python
        capabilities=Capabilities(
            speech=speaker,
            tone=tone_output,
        ),
```

with:

```python
        capabilities=parts.output.capabilities,
```

- [ ] **Step 3: Run NVDA Remote runtime tests**

Run:

```bash
pytest tests/unit/test_app_wx.py -k "nvda_remote or remote" -v
```

Expected: pass.

- [ ] **Step 4: Run M1 focused verification**

Run:

```bash
pytest \
  tests/unit/test_bootstrap_platform.py \
  tests/unit/test_bootstrap_output.py \
  tests/unit/test_bootstrap_app_runtime.py \
  tests/unit/test_key_echo_app_service.py \
  tests/unit/test_access8graph_app_service.py \
  tests/unit/test_nvda_remote_app_service.py \
  tests/unit/test_app_wx.py \
  -v
```

Expected: pass.

- [ ] **Step 5: Commit M1 app entrypoint refactor**

```bash
git add \
  src/apps/nvda_remote/main.py \
  tests/unit/test_app_wx.py
git commit -m "refactor: use shared runtime builder in nvda remote"
```

- [ ] **Step 6: M1 merge checkpoint**

Run:

```bash
pytest tests/unit tests/integration -v
```

Expected: pass. If this is a PR workflow, stop here for review and merge M1 before starting M2.

---

## M2: Typed Event Boundary Across All Apps

### Task 7: Add Shared Typed Application Events

**Files:**
- Create: `tests/unit/test_application_events.py`
- Modify: `src/application/events.py`

- [ ] **Step 1: Write failing shared event tests**

Create `tests/unit/test_application_events.py`:

```python
from application.events import AppEvent
from application.events import ClipboardAvailabilityChanged
from application.events import ErrorRaised
from application.events import HotkeyCaptureChanged
from application.events import InputCaptureChanged
from application.events import ModeChanged
from application.events import SpeechBackendChanged


def test_shared_events_are_frozen_value_objects():
    event = ErrorRaised("boom")

    assert event.message == "boom"
    assert event == ErrorRaised("boom")


def test_app_event_union_accepts_shared_events():
    events: list[AppEvent] = [
        ErrorRaised("boom"),
        SpeechBackendChanged("pyttsx3"),
        InputCaptureChanged(active=True),
        HotkeyCaptureChanged(active=False),
        ClipboardAvailabilityChanged(available=True),
        ModeChanged(mode_id="echo", active=True),
    ]

    assert [type(event).__name__ for event in events] == [
        "ErrorRaised",
        "SpeechBackendChanged",
        "InputCaptureChanged",
        "HotkeyCaptureChanged",
        "ClipboardAvailabilityChanged",
        "ModeChanged",
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/unit/test_application_events.py -v
```

Expected: fail with import errors for the new event classes.

- [ ] **Step 3: Replace shared event definitions**

Replace `src/application/events.py` with:

```python
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ErrorRaised:
    message: str


@dataclass(frozen=True, slots=True)
class SpeechBackendChanged:
    backend_id: str


@dataclass(frozen=True, slots=True)
class InputCaptureChanged:
    active: bool


@dataclass(frozen=True, slots=True)
class HotkeyCaptureChanged:
    active: bool


@dataclass(frozen=True, slots=True)
class ClipboardAvailabilityChanged:
    available: bool


@dataclass(frozen=True, slots=True)
class ModeChanged:
    mode_id: str
    active: bool


AppEvent = (
    ErrorRaised
    | SpeechBackendChanged
    | InputCaptureChanged
    | HotkeyCaptureChanged
    | ClipboardAvailabilityChanged
    | ModeChanged
)


@dataclass(frozen=True, slots=True)
class StatusEvent:
    kind: str
    state: str | None = None
    type: str | None = None
    reason: str | None = None
    payload: dict[str, Any] | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "StatusEvent":
        return cls(
            kind=str(payload.get("kind", "")),
            state=payload.get("state"),
            type=payload.get("type"),
            reason=payload.get("reason"),
            payload=payload.get("payload"),
        )
```

- [ ] **Step 4: Run shared event tests**

Run:

```bash
pytest tests/unit/test_application_events.py -v
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/application/events.py tests/unit/test_application_events.py
git commit -m "feat: add typed application events"
```

### Task 8: Add App-Domain Typed Events

**Files:**
- Create: `tests/unit/test_app_events.py`
- Create: `src/apps/key_echo/events.py`
- Create: `src/apps/access8graph/events.py`
- Create: `src/apps/nvda_remote/events.py`

- [ ] **Step 1: Write failing app event tests**

Create `tests/unit/test_app_events.py`:

```python
from apps.access8graph.events import GraphNavigationChanged
from apps.key_echo.events import EchoStateChanged
from apps.nvda_remote.events import RemoteConnectionChanged
from apps.nvda_remote.events import RemoteControlChanged
from apps.nvda_remote.events import RemoteMessageReceived
from apps.nvda_remote.events import RemoteTransportDisconnected


def test_key_echo_event_models_echo_state():
    assert EchoStateChanged(running=True).running is True


def test_access8graph_event_models_navigation_state():
    assert GraphNavigationChanged(active=False).active is False


def test_nvda_remote_event_models_remote_states():
    assert RemoteConnectionChanged(state="connected").state == "connected"
    assert RemoteControlChanged(state="controlling").state == "controlling"
    assert RemoteTransportDisconnected(reason="closed").reason == "closed"
    assert RemoteMessageReceived(type="motd", payload={"text": "hi"}).payload == {"text": "hi"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/unit/test_app_events.py -v
```

Expected: fail with module import errors for the new event modules.

- [ ] **Step 3: Add Key Echo event module**

Create `src/apps/key_echo/events.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EchoStateChanged:
    running: bool
```

- [ ] **Step 4: Add Access8Graph event module**

Create `src/apps/access8graph/events.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GraphNavigationChanged:
    active: bool
```

- [ ] **Step 5: Add NVDA Remote event module**

Create `src/apps/nvda_remote/events.py`:

```python
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RemoteConnectionChanged:
    state: str


@dataclass(frozen=True, slots=True)
class RemoteControlChanged:
    state: str


@dataclass(frozen=True, slots=True)
class RemoteTransportDisconnected:
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class RemoteMessageReceived:
    type: str
    payload: dict[str, Any]
```

- [ ] **Step 6: Run app event tests**

Run:

```bash
pytest tests/unit/test_app_events.py -v
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add \
  src/apps/key_echo/events.py \
  src/apps/access8graph/events.py \
  src/apps/nvda_remote/events.py \
  tests/unit/test_app_events.py
git commit -m "feat: add app typed events"
```

### Task 9: Migrate Shared Mode Manager To Typed Events

**Files:**
- Modify: `tests/unit/test_mode_manager.py`
- Modify: `src/apps/shared/mode_manager.py`

- [ ] **Step 1: Update mode manager tests to expect typed events**

In `tests/unit/test_mode_manager.py`, replace dict assertions for mode status with `ModeChanged` assertions:

```python
from application.events import ModeChanged
```

Expected assertion shape:

```python
assert statuses == [ModeChanged(mode_id="echo", active=True)]
```

For active then idle assertions:

```python
assert statuses == [
    ModeChanged(mode_id="echo", active=True),
    ModeChanged(mode_id="echo", active=False),
]
```

- [ ] **Step 2: Run mode manager tests to verify they fail**

Run:

```bash
pytest tests/unit/test_mode_manager.py -v
```

Expected: fail because `mode_manager.py` still emits dict statuses.

- [ ] **Step 3: Emit `ModeChanged` from mode manager**

In `src/apps/shared/mode_manager.py`, add:

```python
from application.events import ModeChanged
```

Replace active dict emission:

```python
self._notify_status({"kind": "mode", "mode_id": mode_id, "state": "active"})
```

with:

```python
self._notify_status(ModeChanged(mode_id=mode_id, active=True))
```

Replace idle dict emission:

```python
self._notify_status({"kind": "mode", "mode_id": mode_id, "state": "idle"})
```

with:

```python
self._notify_status(ModeChanged(mode_id=mode_id, active=False))
```

- [ ] **Step 4: Run mode manager tests**

Run:

```bash
pytest tests/unit/test_mode_manager.py -v
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/apps/shared/mode_manager.py tests/unit/test_mode_manager.py
git commit -m "refactor: emit typed mode events"
```

### Task 10: Migrate Key Echo Service And Use Cases To Typed Events

**Files:**
- Modify: `tests/unit/test_key_echo_use_cases.py`
- Modify: `tests/unit/test_key_echo_app_service.py`
- Modify: `src/apps/key_echo/use_cases/echo_control.py`
- Modify: `src/apps/key_echo/service.py`

- [ ] **Step 1: Update Key Echo use-case tests**

In `tests/unit/test_key_echo_use_cases.py`, import:

```python
from apps.key_echo.events import EchoStateChanged
```

Replace echo status dict expectations:

```python
assert statuses == [
    EchoStateChanged(running=True),
    EchoStateChanged(running=False),
]
```

- [ ] **Step 2: Run use-case tests to verify they fail**

Run:

```bash
pytest tests/unit/test_key_echo_use_cases.py -v
```

Expected: fail because `echo_control.py` still emits dict statuses.

- [ ] **Step 3: Update echo control use case**

In `src/apps/key_echo/use_cases/echo_control.py`, add:

```python
from apps.key_echo.events import EchoStateChanged
```

Replace running emission:

```python
self._notify_status({"kind": "echo", "state": "running"})
```

with:

```python
self._notify_status(EchoStateChanged(running=True))
```

Replace stopped emission:

```python
self._notify_status({"kind": "echo", "state": "stopped"})
```

with:

```python
self._notify_status(EchoStateChanged(running=False))
```

- [ ] **Step 4: Run Key Echo use-case tests**

Run:

```bash
pytest tests/unit/test_key_echo_use_cases.py -v
```

Expected: pass.

- [ ] **Step 5: Update Key Echo app service tests**

In `tests/unit/test_key_echo_app_service.py`, import:

```python
from application.events import ErrorRaised
from application.events import SpeechBackendChanged
from apps.key_echo.events import EchoStateChanged
```

Replace speech backend status assertion:

```python
assert delivered == [SpeechBackendChanged("default")]
```

Replace error status assertions:

```python
assert delivered == [ErrorRaised("No input capture available")]
```

Replace echo status assertions:

```python
assert delivered == [EchoStateChanged(running=True)]
```

- [ ] **Step 6: Run app service tests to verify they fail**

Run:

```bash
pytest tests/unit/test_key_echo_app_service.py -v
```

Expected: fail because `service.py` still emits dict statuses.

- [ ] **Step 7: Update Key Echo service emission**

In `src/apps/key_echo/service.py`, add:

```python
from application.events import ErrorRaised
from application.events import SpeechBackendChanged
```

Replace notify error lambdas like:

```python
notify_error=lambda message: self._notify_status_listener(
    {"kind": "error", "message": message}
)
```

with:

```python
notify_error=lambda message: self._notify_status_listener(ErrorRaised(message))
```

Replace speech backend event:

```python
self._notify_status_listener({"kind": "speech_backend", "backend_id": backend_id})
```

with:

```python
self._notify_status_listener(SpeechBackendChanged(backend_id))
```

Change `_notify_status_listener` signature:

```python
def _notify_status_listener(self, event) -> None:
    if self._status_listener is not None:
        self._status_listener(event)
```

- [ ] **Step 8: Run Key Echo tests**

Run:

```bash
pytest tests/unit/test_key_echo_use_cases.py tests/unit/test_key_echo_app_service.py -v
```

Expected: pass.

- [ ] **Step 9: Commit**

```bash
git add \
  src/apps/key_echo/use_cases/echo_control.py \
  src/apps/key_echo/service.py \
  tests/unit/test_key_echo_use_cases.py \
  tests/unit/test_key_echo_app_service.py
git commit -m "refactor: migrate key echo typed events"
```

### Task 11: Migrate Access8Graph Service To Typed Events

**Files:**
- Modify: `tests/unit/test_access8graph_app_service.py`
- Modify: `src/apps/access8graph/service.py`

- [ ] **Step 1: Update Access8Graph app service tests**

In `tests/unit/test_access8graph_app_service.py`, import:

```python
from application.events import ErrorRaised
from application.events import SpeechBackendChanged
from apps.access8graph.events import GraphNavigationChanged
```

Replace speech backend assertion:

```python
assert delivered == [SpeechBackendChanged("default")]
```

Replace error assertions:

```python
assert delivered == [ErrorRaised("No GraphML file selected")]
```

Replace failed navigation assertion:

```python
assert delivered == [ErrorRaised("Failed to start navigation")]
```

Replace status containment assertion:

```python
assert ErrorRaised("flow dispatch failed") in statuses
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/unit/test_access8graph_app_service.py -v
```

Expected: fail because `service.py` still emits dict statuses.

- [ ] **Step 3: Update Access8Graph service emission**

In `src/apps/access8graph/service.py`, add:

```python
from application.events import ErrorRaised
from application.events import SpeechBackendChanged
```

Replace error emissions:

```python
self._notify_status_listener({"kind": "error", "message": str(error)})
```

with:

```python
self._notify_status_listener(ErrorRaised(str(error)))
```

Replace error lambda:

```python
notify_error=lambda message: self._notify_status_listener(
    {"kind": "error", "message": message}
)
```

with:

```python
notify_error=lambda message: self._notify_status_listener(ErrorRaised(message))
```

Replace speech backend event:

```python
self._notify_status_listener({"kind": "speech_backend", "backend_id": backend_id})
```

with:

```python
self._notify_status_listener(SpeechBackendChanged(backend_id))
```

Change `_notify_status_listener` so it only handles `ErrorRaised` specially:

```python
def _notify_status_listener(self, event) -> None:
    if isinstance(event, ErrorRaised) and self._capabilities.speech is not None:
        self._capabilities.speech.speak(event.message)
    if self._status_listener is not None:
        self._main_thread_dispatch(lambda: self._status_listener(event))
```

- [ ] **Step 4: Run Access8Graph service tests**

Run:

```bash
pytest tests/unit/test_access8graph_app_service.py -v
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/apps/access8graph/service.py tests/unit/test_access8graph_app_service.py
git commit -m "refactor: migrate access8graph typed events"
```

### Task 12: Migrate NVDA Remote Service And Use Cases To Typed Events

**Files:**
- Modify: `tests/unit/test_nvda_remote_use_cases.py`
- Modify: `tests/unit/test_nvda_remote_app_service.py`
- Modify: `tests/unit/test_message_router.py`
- Modify: `src/apps/nvda_remote/use_cases/control_mode.py`
- Modify: `src/apps/nvda_remote/service.py`

- [ ] **Step 1: Update NVDA Remote use-case tests**

In `tests/unit/test_nvda_remote_use_cases.py`, import:

```python
from apps.nvda_remote.events import RemoteControlChanged
```

Replace control status assertions:

```python
assert notifications == [RemoteControlChanged(ControlState.CONTROLLING.value)]
```

and:

```python
assert notifications == [RemoteControlChanged(ControlState.CONNECTED.value)]
```

- [ ] **Step 2: Run use-case tests to verify they fail**

Run:

```bash
pytest tests/unit/test_nvda_remote_use_cases.py -v
```

Expected: fail because `control_mode.py` still emits dict statuses.

- [ ] **Step 3: Update remote control use case**

In `src/apps/nvda_remote/use_cases/control_mode.py`, add:

```python
from apps.nvda_remote.events import RemoteControlChanged
```

Replace:

```python
self._notify_status({"kind": "control", "state": ControlState.CONTROLLING.value})
```

with:

```python
self._notify_status(RemoteControlChanged(ControlState.CONTROLLING.value))
```

Replace:

```python
self._notify_status({"kind": "control", "state": ControlState.CONNECTED.value})
```

with:

```python
self._notify_status(RemoteControlChanged(ControlState.CONNECTED.value))
```

- [ ] **Step 4: Run use-case tests**

Run:

```bash
pytest tests/unit/test_nvda_remote_use_cases.py -v
```

Expected: pass.

- [ ] **Step 5: Update NVDA Remote app service tests**

In `tests/unit/test_nvda_remote_app_service.py`, import:

```python
from application.events import ErrorRaised
from application.events import SpeechBackendChanged
from apps.nvda_remote.events import RemoteConnectionChanged
```

Replace connection status assertions:

```python
assert delivered == [RemoteConnectionChanged("connected")]
```

Replace idle status assertions:

```python
assert status_events == [RemoteConnectionChanged("idle")]
```

Replace error status assertions:

```python
assert status_events == [ErrorRaised("hotkey busy")]
```

Replace speech backend assertions:

```python
assert delivered == [SpeechBackendChanged("pyttsx3")]
```

- [ ] **Step 6: Run app service tests to verify they fail**

Run:

```bash
pytest tests/unit/test_nvda_remote_app_service.py -v
```

Expected: fail because `service.py` still emits dict statuses.

- [ ] **Step 7: Update NVDA Remote service emission**

In `src/apps/nvda_remote/service.py`, add:

```python
from application.events import ErrorRaised
from application.events import SpeechBackendChanged
from apps.nvda_remote.events import RemoteConnectionChanged
```

Replace speech backend event:

```python
self._notify_status_listener({"kind": "speech_backend", "backend_id": backend_id})
```

with:

```python
self._notify_status_listener(SpeechBackendChanged(backend_id))
```

Replace explicit idle status:

```python
self._on_status({"kind": "connection", "state": "idle"})
```

with:

```python
self._on_status(RemoteConnectionChanged("idle"))
```

Replace `_on_status()` dict handling with typed connection handling:

```python
def _on_status(self, status) -> None:
    if not isinstance(status, RemoteConnectionChanged):
        self._notify_status_listener(status)
        return
    match status.state:
        case "connected":
            self._state.connection_state = "connected"
        case "idle":
            self._state.connection_state = "idle"
        case _:
            self._state.connection_state = status.state
    self._notify_status_listener(status)
```

Replace:

```python
self._notify_status_listener({"kind": "error", "message": message})
```

with:

```python
self._notify_status_listener(ErrorRaised(message))
```

- [ ] **Step 8: Keep router tests isolated from app/UI typed boundary**

If `tests/unit/test_message_router.py` still asserts dict statuses from interop routing, leave those assertions in place unless the service boundary now directly consumes them. The M2 scope is app service to UI/controller listeners, not protocol wire/message-router internals.

- [ ] **Step 9: Run NVDA Remote focused tests**

Run:

```bash
pytest \
  tests/unit/test_nvda_remote_use_cases.py \
  tests/unit/test_nvda_remote_app_service.py \
  tests/unit/test_message_router.py \
  -v
```

Expected: pass.

- [ ] **Step 10: Commit**

```bash
git add \
  src/apps/nvda_remote/use_cases/control_mode.py \
  src/apps/nvda_remote/service.py \
  tests/unit/test_nvda_remote_use_cases.py \
  tests/unit/test_nvda_remote_app_service.py \
  tests/unit/test_message_router.py
git commit -m "refactor: migrate nvda remote typed events"
```

### Task 13: Migrate UI Status Consumers To Typed Events

**Files:**
- Modify: `tests/unit/test_app_wx.py`
- Modify: `tests/unit/test_access8graph_ui.py`
- Modify: `src/ui/echo/main_frame.py`
- Modify: `src/ui/access8graph/main_frame.py`
- Modify: `src/ui/nvda_remote/main_frame.py`

- [ ] **Step 1: Update fake controllers in UI tests**

In `tests/unit/test_app_wx.py`, import:

```python
from application.events import ErrorRaised
from application.events import SpeechBackendChanged
from apps.key_echo.events import EchoStateChanged
from apps.nvda_remote.events import RemoteConnectionChanged
```

Replace fake-controller status calls:

```python
self.status_listener(RemoteConnectionChanged("connected"))
self.status_listener(RemoteConnectionChanged("idle"))
self.status_listener(SpeechBackendChanged(backend_id))
self.status_listener(EchoStateChanged(running=True))
self.status_listener(EchoStateChanged(running=False))
self.status_listener(ErrorRaised("permissions missing"))
```

In `tests/unit/test_access8graph_ui.py`, import:

```python
from application.events import ErrorRaised
```

Replace:

```python
self.listener({"kind": "error", "message": self.start_error})
controller.listener({"kind": "error", "message": "Something went wrong"})
controller.listener({"kind": "error", "message": "parse failed"})
```

with:

```python
self.listener(ErrorRaised(self.start_error))
controller.listener(ErrorRaised("Something went wrong"))
controller.listener(ErrorRaised("parse failed"))
```

- [ ] **Step 2: Run UI tests to verify they fail**

Run:

```bash
pytest tests/unit/test_app_wx.py tests/unit/test_access8graph_ui.py -v
```

Expected: fail because UI frames still inspect dict keys.

- [ ] **Step 3: Update Echo main frame typed event handling**

In `src/ui/echo/main_frame.py`, add:

```python
from apps.key_echo.events import EchoStateChanged
```

Replace `_on_controller_status()` with:

```python
def _on_controller_status(self, event) -> None:
    if isinstance(event, EchoStateChanged):
        self.status_label.SetLabel("Running" if event.running else "Stopped")
        self.control_button.SetLabel("Stop" if event.running else "Start")
        return
    self._sync_echo_controls()
```

- [ ] **Step 4: Update Access8Graph main frame typed event handling**

In `src/ui/access8graph/main_frame.py`, add:

```python
from application.events import ErrorRaised
from apps.access8graph.events import GraphNavigationChanged
```

Replace dict checks like:

```python
if isinstance(status, dict) and status.get("kind") == "error":
    self._last_error = str(status.get("message", ""))
```

with:

```python
if isinstance(status, ErrorRaised):
    self._last_error = status.message
    self.status_label.SetLabel(self._last_error)
    return
```

Add a graph navigation branch before clearing `_last_error`:

```python
if isinstance(status, GraphNavigationChanged):
    self.navigation_button.SetLabel(
        "Stop Navigation" if status.active else "Start Navigation"
    )
```

Keep the existing final sync:

```python
self._last_error = None
self._sync_controls()
```

- [ ] **Step 5: Update NVDA Remote main frame typed event handling**

In `src/ui/nvda_remote/main_frame.py`, add:

```python
from application.events import ErrorRaised
from apps.nvda_remote.events import RemoteConnectionChanged
from apps.nvda_remote.events import RemoteControlChanged
```

Replace `_on_controller_status()` with:

```python
def _on_controller_status(self, event) -> None:
    if isinstance(event, ErrorRaised) and event.message:
        self._show_error(event.message, "Input Error")
    self._sync_connect_button_label()
    self._sync_control_button()
    self._sync_connection_fields()
    self._sync_clipboard_button()
```

`RemoteConnectionChanged` and `RemoteControlChanged` do not need direct widget mutation in this frame because the service updates `controller.state`; the sync helpers read from that state.

- [ ] **Step 6: Run UI tests**

Run:

```bash
pytest tests/unit/test_app_wx.py tests/unit/test_access8graph_ui.py -v
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add \
  src/ui/echo/main_frame.py \
  src/ui/access8graph/main_frame.py \
  src/ui/nvda_remote/main_frame.py \
  tests/unit/test_app_wx.py \
  tests/unit/test_access8graph_ui.py
git commit -m "refactor: migrate UI status consumers to typed events"
```

### Task 14: Remove Dict-First App/UI Status Flow

**Files:**
- Modify: any remaining app/UI files reported by the scan below.

- [ ] **Step 1: Scan for remaining dict-first status patterns**

Run:

```bash
rg -n '\{"kind"|status\.get\("kind"|status\["kind"\]|_status\.get\("kind"|set_status_listener' src/apps src/ui tests/unit
```

Expected: remaining matches are limited to protocol/message-router tests, transitional `StatusEvent.from_payload()` tests, and listener registration method names.

- [ ] **Step 2: Fix remaining app/UI dict emissions**

For any remaining match in `src/apps/key_echo`, `src/apps/access8graph`, `src/apps/nvda_remote`, or `src/ui`, replace dict status payloads with the typed events defined in Tasks 7 and 8.

Use this mapping:

```python
{"kind": "error", "message": message} -> ErrorRaised(message)
{"kind": "speech_backend", "backend_id": backend_id} -> SpeechBackendChanged(backend_id)
{"kind": "echo", "state": "running"} -> EchoStateChanged(running=True)
{"kind": "echo", "state": "stopped"} -> EchoStateChanged(running=False)
{"kind": "connection", "state": state} -> RemoteConnectionChanged(state)
{"kind": "control", "state": state} -> RemoteControlChanged(state)
{"kind": "mode", "mode_id": mode_id, "state": "active"} -> ModeChanged(mode_id=mode_id, active=True)
{"kind": "mode", "mode_id": mode_id, "state": "idle"} -> ModeChanged(mode_id=mode_id, active=False)
```

- [ ] **Step 3: Run M2 focused verification**

Run:

```bash
pytest \
  tests/unit/test_application_events.py \
  tests/unit/test_app_events.py \
  tests/unit/test_mode_manager.py \
  tests/unit/test_key_echo_use_cases.py \
  tests/unit/test_key_echo_app_service.py \
  tests/unit/test_access8graph_app_service.py \
  tests/unit/test_nvda_remote_use_cases.py \
  tests/unit/test_nvda_remote_app_service.py \
  tests/unit/test_app_wx.py \
  tests/unit/test_access8graph_ui.py \
  -v
```

Expected: pass.

- [ ] **Step 4: Run final verification**

Run:

```bash
pytest tests/unit tests/integration -v
```

Expected: pass.

- [ ] **Step 5: Commit cleanup**

```bash
git add src/apps src/application src/ui tests/unit
git commit -m "refactor: remove dict-first app status flow"
```

---

## Final Review Checklist

- [ ] M1 app entrypoints no longer open-code shared `Scheduler`, `SpeechService`, `QueuedService`, `Capabilities`, input capture, hotkey capture, clipboard, and tone assembly.
- [ ] `bootstrap/platform.py` remains the platform detection/fallback owner and does not become a general dependency container.
- [ ] `bootstrap/output.py` owns only output service assembly.
- [ ] `bootstrap/app_runtime.py` owns only common app runtime parts.
- [ ] `application/events.py` contains shared runtime/capability events.
- [ ] App-domain event modules contain app-specific events only.
- [ ] All three app services emit typed events to UI-facing listeners.
- [ ] UI consumers use `isinstance()` checks against typed events instead of raw dict key conventions.
- [ ] Protocol/message-router dict payload tests are not expanded into UI event API guarantees.
- [ ] `pytest tests/unit tests/integration -v` passes before declaring implementation complete.
