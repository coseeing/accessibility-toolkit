# Access8Graph Facade And Shared Speech Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thin `Access8GraphAppService`, extract shared speech settings into an independent facade, and retire `application.output.Manager` while preserving current user-facing behavior.

**Architecture:** Implement the approved design in four milestones that can be reviewed independently: Access8Graph lifecycle extraction, Access8Graph command dispatch extraction, shared speech settings facade extraction, and output manager removal. Keep UI-facing behavior stable and use focused tests at each new boundary before rewiring app services.

**Tech Stack:** Python 3.11+, pytest, wxPython-compatible app classes, existing `ModeManager`, `InputActivationUseCase`, `SpeechSettingsController`, `Capabilities`, `MessageRouter`, dataclasses/protocol-style collaborators

---

## Source Spec

Implement from:

- `docs/superpowers/specs/2026-06-26-access8graph-facade-and-shared-speech-settings-design.md`

## File Structure

| File | Responsibility |
|---|---|
| `src/apps/access8graph/use_cases/graph_selection.py` | Own GraphML path validation and selected path state |
| `src/apps/access8graph/use_cases/navigation.py` | Own Access8Graph flow construction, lifecycle, active state, and navigation event dispatch |
| `src/apps/access8graph/use_cases/command_dispatch.py` | Own command translation and dispatch to the active navigation flow |
| `src/apps/access8graph/use_cases/__init__.py` | Export Access8Graph use cases |
| `src/apps/access8graph/service.py` | Remain the UI-facing facade and compose Access8Graph use cases |
| `tests/unit/test_access8graph_use_cases.py` | Focused tests for graph selection, navigation lifecycle, and command dispatch |
| `tests/unit/test_access8graph_app_service.py` | Regression tests for service behavior after refactor |
| `src/apps/shared/speech_settings_facade.py` | Independent shared speech settings facade |
| `src/apps/shared/speech_settings_controller.py` | Compatibility import during migration, then optional removal in a later cleanup |
| `src/apps/shared/tool_app_shell.py` | Accept separate main controller and speech settings controller |
| `src/ui/shared/speech_settings_frame.py` | Continue to receive a speech settings controller-shaped object |
| `src/ui/nvda_remote/app.py` | Pass app service and speech settings facade separately into `ToolAppShell` |
| `src/ui/echo/app.py` | Pass app service and speech settings facade separately into `ToolAppShell` |
| `src/ui/access8graph/app.py` | Pass app service and speech settings facade separately into `ToolAppShell` |
| `src/apps/nvda_remote/main.py` | Build shared speech settings facade outside the app service |
| `src/apps/key_echo/main.py` | Build shared speech settings facade outside the app service |
| `src/apps/access8graph/main.py` | Build shared speech settings facade outside the app service |
| `src/apps/nvda_remote/service.py` | Remove speech settings pass-through methods after UI wiring moves to facade |
| `src/apps/key_echo/service.py` | Remove speech settings pass-through methods after UI wiring moves to facade |
| `src/application/output/manager.py` | Delete retired output manager |
| `src/application/output/__init__.py` | Stop exporting `Manager`; keep or relocate `ClipboardService` protocol |
| `src/application/output/clipboard.py` | New home for `ClipboardService` protocol if it remains shared |
| `tests/unit/test_speech_settings_facade.py` | Focused tests for independent speech settings facade |
| `tests/unit/test_tool_app_shell.py` | Verify speech frame receives separate speech settings controller |
| `tests/unit/test_output_service.py` | Update export/import tests after `Manager` removal |
| `tests/unit/test_message_router.py` | Replace `Manager` usage in router tests with explicit fake callbacks |
| `tests/unit/test_speech_backends.py` | Replace `Manager` usage with direct speech output calls or local callback wiring |
| `tests/unit/test_output_manager.py` | Delete or replace with tests for surviving output behavior |

## Milestone 1: Access8Graph Flow Lifecycle And Facade Narrowing

### Task 1: Add Graph Selection And Navigation Lifecycle Use Cases

**Files:**
- Create: `src/apps/access8graph/use_cases/__init__.py`
- Create: `src/apps/access8graph/use_cases/graph_selection.py`
- Create: `src/apps/access8graph/use_cases/navigation.py`
- Create: `tests/unit/test_access8graph_use_cases.py`

- [ ] **Step 1: Write failing graph selection tests**

Create `tests/unit/test_access8graph_use_cases.py` with these initial tests:

```python
from pathlib import Path

import pytest

from apps.access8graph.events import GraphNavigationChanged
from apps.access8graph.use_cases.graph_selection import GraphSelectionUseCase
from apps.access8graph.use_cases.navigation import Access8GraphNavigationSession


def test_graph_selection_accepts_existing_graphml_file(tmp_path: Path) -> None:
    path = tmp_path / "map.GRAPHML"
    path.write_text("<graphml />", encoding="utf-8")
    selection = GraphSelectionUseCase()

    selection.choose_graphml(str(path))

    assert selection.get_selected_graphml_path() == str(path)
    assert selection.require_existing_graphml_path() == path


def test_graph_selection_rejects_non_graphml_file(tmp_path: Path) -> None:
    path = tmp_path / "map.txt"
    path.write_text("<graphml />", encoding="utf-8")
    selection = GraphSelectionUseCase()

    with pytest.raises(ValueError, match="\\.graphml"):
        selection.choose_graphml(str(path))


def test_graph_selection_rejects_missing_file() -> None:
    selection = GraphSelectionUseCase()

    with pytest.raises(FileNotFoundError):
        selection.choose_graphml("/missing/map.graphml")


def test_graph_selection_requires_selected_path_before_start() -> None:
    selection = GraphSelectionUseCase()

    with pytest.raises(RuntimeError, match="No GraphML file selected"):
        selection.require_existing_graphml_path()
```

- [ ] **Step 2: Run graph selection tests and verify they fail**

Run:

```bash
pytest tests/unit/test_access8graph_use_cases.py -k graph_selection -v
```

Expected: FAIL because `apps.access8graph.use_cases.graph_selection` does not exist.

- [ ] **Step 3: Implement `GraphSelectionUseCase`**

Create `src/apps/access8graph/use_cases/graph_selection.py`:

```python
from pathlib import Path


class GraphSelectionUseCase:
    def __init__(self) -> None:
        self._selected_path: str | None = None

    def choose_graphml(self, path: str) -> None:
        graphml_path = Path(path)
        if graphml_path.suffix.lower() != ".graphml":
            raise ValueError("Selected file must have a .graphml extension")
        if not graphml_path.is_file():
            raise FileNotFoundError(str(graphml_path))
        self._selected_path = str(graphml_path)

    def get_selected_graphml_path(self) -> str | None:
        return self._selected_path

    def require_existing_graphml_path(self) -> Path:
        if self._selected_path is None:
            raise RuntimeError("No GraphML file selected")
        graphml_path = Path(self._selected_path)
        if not graphml_path.is_file():
            raise FileNotFoundError(
                f"GraphML file no longer exists: {self._selected_path}"
            )
        return graphml_path
```

Create `src/apps/access8graph/use_cases/__init__.py`:

```python
from apps.access8graph.use_cases.graph_selection import GraphSelectionUseCase

__all__ = ["GraphSelectionUseCase"]
```

- [ ] **Step 4: Run graph selection tests and verify they pass**

Run:

```bash
pytest tests/unit/test_access8graph_use_cases.py -k graph_selection -v
```

Expected: PASS.

- [ ] **Step 5: Add failing navigation session tests**

Append to `tests/unit/test_access8graph_use_cases.py`:

```python
class FakeFlowOutput:
    def __init__(self) -> None:
        self.cancel_count = 0

    def cancel_speech(self) -> None:
        self.cancel_count += 1


class FakeFlowFactory:
    def __init__(self) -> None:
        self.paths = []
        self.flow = object()

    def create(self, path: Path):
        self.paths.append(path)
        return self.flow


def test_navigation_session_starts_flow_and_reports_active_state(tmp_path: Path) -> None:
    path = tmp_path / "map.graphml"
    path.write_text("<graphml />", encoding="utf-8")
    selection = GraphSelectionUseCase()
    selection.choose_graphml(str(path))
    statuses = []
    output = FakeFlowOutput()
    factory = FakeFlowFactory()
    session = Access8GraphNavigationSession(
        graph_selection=selection,
        flow_factory=factory,
        flow_output=output,
        notify_status=statuses.append,
    )

    session.set_active(True)
    session.start_flow()

    assert session.is_active() is True
    assert session.current_flow is factory.flow
    assert factory.paths == [path]
    assert statuses == [GraphNavigationChanged(active=True)]


def test_navigation_session_stop_flow_clears_flow_cancels_speech_and_reports_state(
    tmp_path: Path,
) -> None:
    path = tmp_path / "map.graphml"
    path.write_text("<graphml />", encoding="utf-8")
    selection = GraphSelectionUseCase()
    selection.choose_graphml(str(path))
    statuses = []
    output = FakeFlowOutput()
    factory = FakeFlowFactory()
    session = Access8GraphNavigationSession(
        graph_selection=selection,
        flow_factory=factory,
        flow_output=output,
        notify_status=statuses.append,
    )
    session.set_active(True)
    session.start_flow()
    statuses.clear()

    session.stop_flow()

    assert session.is_active() is False
    assert session.current_flow is None
    assert output.cancel_count == 1
    assert statuses == [GraphNavigationChanged(active=False)]
```

- [ ] **Step 6: Run navigation session tests and verify they fail**

Run:

```bash
pytest tests/unit/test_access8graph_use_cases.py -k navigation_session -v
```

Expected: FAIL because `Access8GraphNavigationSession` does not exist.

- [ ] **Step 7: Implement navigation lifecycle classes**

Create `src/apps/access8graph/use_cases/navigation.py`:

```python
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from apps.access8graph.events import GraphNavigationChanged
from apps.access8graph.flow import MrtFlow
from apps.access8graph.graphml import (
    Graph,
    MrtDirectionNavigator,
    MrtModel,
    MrtUndirectionNavigator,
)


class FlowOutput(Protocol):
    def cancel_speech(self) -> None: ...


class FlowFactory(Protocol):
    def create(self, path: Path): ...


class MrtFlowFactory:
    def __init__(self, *, output) -> None:
        self._output = output

    def create(self, path: Path) -> MrtFlow:
        graph = Graph(path=str(path))
        model = MrtModel(graph)
        return MrtFlow(
            navigator={
                "direction": MrtDirectionNavigator(model),
                "undirection": MrtUndirectionNavigator(model),
            },
            output=self._output,
        )


class Access8GraphNavigationSession:
    def __init__(
        self,
        *,
        graph_selection,
        flow_factory: FlowFactory,
        flow_output: FlowOutput,
        notify_status: Callable[[GraphNavigationChanged], None],
    ) -> None:
        self._graph_selection = graph_selection
        self._flow_factory = flow_factory
        self._flow_output = flow_output
        self._notify_status = notify_status
        self._active = False
        self._flow = None

    @property
    def current_flow(self):
        return self._flow

    def is_active(self) -> bool:
        return self._active

    def set_active(self, active: bool) -> None:
        self._active = active

    def can_start(self) -> bool:
        return self._graph_selection.get_selected_graphml_path() is not None

    def start_flow(self) -> None:
        path = self._graph_selection.require_existing_graphml_path()
        self._flow = self._flow_factory.create(path)
        self._notify_status(GraphNavigationChanged(active=True))

    def stop_flow(self) -> None:
        had_flow = self._flow is not None
        self._active = False
        self._flow = None
        self._flow_output.cancel_speech()
        if had_flow:
            self._notify_status(GraphNavigationChanged(active=False))
```

Update `src/apps/access8graph/use_cases/__init__.py`:

```python
from apps.access8graph.use_cases.graph_selection import GraphSelectionUseCase
from apps.access8graph.use_cases.navigation import (
    Access8GraphNavigationSession,
    MrtFlowFactory,
)

__all__ = [
    "Access8GraphNavigationSession",
    "GraphSelectionUseCase",
    "MrtFlowFactory",
]
```

- [ ] **Step 8: Run use case tests**

Run:

```bash
pytest tests/unit/test_access8graph_use_cases.py -v
```

Expected: PASS.

- [ ] **Step 9: Commit milestone 1 use cases**

```bash
git add src/apps/access8graph/use_cases tests/unit/test_access8graph_use_cases.py
git commit -m "refactor: add access8graph navigation use cases"
```

### Task 2: Rewire `Access8GraphAppService` To Use Lifecycle Use Cases

**Files:**
- Modify: `src/apps/access8graph/service.py`
- Modify: `tests/unit/test_access8graph_app_service.py`

- [ ] **Step 1: Add service regression tests for private-method removal behavior**

Append to `tests/unit/test_access8graph_app_service.py`:

```python
def test_navigation_mode_does_not_require_service_private_flow_methods() -> None:
    service, _input_capture, _hotkey_capture, _speech = build_service()
    service.choose_graphml(str(FIXTURE))

    assert not hasattr(service, "_start_flow")
    assert not hasattr(service, "_stop_flow")


def test_service_keeps_selected_graphml_after_lifecycle_extraction() -> None:
    service, _input_capture, _hotkey_capture, _speech = build_service()

    service.choose_graphml(str(FIXTURE))

    assert service.get_selected_graphml_path() == str(FIXTURE)
```

- [ ] **Step 2: Run targeted service tests and verify new test fails**

Run:

```bash
pytest tests/unit/test_access8graph_app_service.py -k "private_flow_methods or selected_graphml_after" -v
```

Expected: FAIL because `Access8GraphAppService` still has `_start_flow` and `_stop_flow`.

- [ ] **Step 3: Replace direct lifecycle state in `Access8GraphAppService`**

In `src/apps/access8graph/service.py`, remove these imports:

```python
from pathlib import Path
from apps.access8graph.flow import MrtFlow
from apps.access8graph.graphml import Graph, MrtDirectionNavigator, MrtModel, MrtUndirectionNavigator
```

Add these imports:

```python
from apps.access8graph.use_cases import (
    Access8GraphNavigationSession,
    GraphSelectionUseCase,
    MrtFlowFactory,
)
```

In `Access8GraphAppService.__init__`, remove:

```python
self._selected_path: str | None = None
self._navigation_running = False
self._flow = None
```

Add after `_flow_output` is created:

```python
self._graph_selection = GraphSelectionUseCase()
self._navigation = Access8GraphNavigationSession(
    graph_selection=self._graph_selection,
    flow_factory=MrtFlowFactory(output=self._flow_output),
    flow_output=self._flow_output,
    notify_status=self._notify_status_listener,
)
```

Change `InputActivationUseCase` construction to use the navigation session:

```python
self._activation = InputActivationUseCase(
    input_capture=input_capture,
    hotkey_capture=hotkey_capture,
    is_active=self._navigation.is_active,
    set_active=self._navigation.set_active,
    notify_error=lambda message: self._notify_status_listener(
        ErrorRaised(message)
    ),
)
```

- [ ] **Step 4: Replace service methods with delegation**

Replace these methods in `Access8GraphAppService`:

```python
def choose_graphml(self, path: str) -> None:
    self._graph_selection.choose_graphml(path)

def get_selected_graphml_path(self) -> str | None:
    return self._graph_selection.get_selected_graphml_path()

def start_navigation(self) -> None:
    if not self._mode_manager.activate_mode("navigation"):
        raise RuntimeError("Failed to start navigation")

def stop_navigation(self) -> None:
    if self._mode_manager.active_mode_id == "navigation":
        self._mode_manager.exit_active_mode()
    else:
        self._navigation.stop_flow()

def is_navigation_running(self) -> bool:
    return self._navigation.is_active()
```

Delete these methods from `Access8GraphAppService`:

```python
def _set_navigation_active(self, active: bool) -> None:
    ...

def _start_flow(self) -> None:
    ...

def _stop_flow(self) -> None:
    ...
```

- [ ] **Step 5: Rewire `Access8GraphNavigationMode`**

Replace `Access8GraphNavigationMode` with:

```python
class Access8GraphNavigationMode:
    mode_id = "navigation"
    enter_usage = HID.F10
    exit_usage = HID.ESCAPE

    def __init__(self, navigation):
        self._navigation = navigation

    def can_enter(self) -> bool:
        return self._navigation.can_start()

    def enter(self) -> bool:
        self._navigation.start_flow()
        return True

    def exit(self) -> bool:
        self._navigation.stop_flow()
        return True

    def handle_key_event(self, event):
        translator = Access8GraphKeyTranslator()
        command = translator.translate(event)
        if command is None:
            return AppKeyEventResult.HANDLED_STOP
        flow = self._navigation.current_flow
        if flow is None:
            return AppKeyEventResult.UNHANDLED
        flow.enter(command)
        return AppKeyEventResult.HANDLED_STOP
```

In `attach_input_service`, register the mode with the navigation session:

```python
self._mode_manager.register(
    Access8GraphNavigationMode(self._navigation)
)
```

- [ ] **Step 6: Run Access8Graph regression tests**

Run:

```bash
pytest tests/unit/test_access8graph_use_cases.py tests/unit/test_access8graph_app_service.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit milestone 1 service rewire**

```bash
git add src/apps/access8graph/service.py tests/unit/test_access8graph_app_service.py
git commit -m "refactor: move access8graph flow lifecycle out of app service"
```

## Milestone 2: Access8Graph Command Translation Boundary

### Task 3: Add Command Dispatcher And Rewire Navigation Mode

**Files:**
- Create: `src/apps/access8graph/use_cases/command_dispatch.py`
- Modify: `src/apps/access8graph/use_cases/__init__.py`
- Modify: `src/apps/access8graph/service.py`
- Modify: `tests/unit/test_access8graph_use_cases.py`
- Modify: `tests/unit/test_access8graph_app_service.py`

- [ ] **Step 1: Add failing command dispatcher tests**

Append to `tests/unit/test_access8graph_use_cases.py`:

```python
from application.input.results import AppKeyEventResult
from apps.access8graph.use_cases.command_dispatch import Access8GraphCommandDispatcher
from interop.key import HID, KeyEvent


class FakeTranslator:
    def __init__(self, command) -> None:
        self.command = command
        self.events = []

    def translate(self, event):
        self.events.append(event)
        return self.command


class FakeNavigationWithFlow:
    def __init__(self, flow) -> None:
        self.current_flow = flow


class RecordingFlow:
    def __init__(self) -> None:
        self.commands = []

    def enter(self, command) -> bool:
        self.commands.append(command)
        return True


def test_command_dispatcher_consumes_unknown_keys() -> None:
    dispatcher = Access8GraphCommandDispatcher(
        translator=FakeTranslator(None),
        navigation=FakeNavigationWithFlow(RecordingFlow()),
    )

    result = dispatcher.handle_key_event(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.F1, pressed=True)
    )

    assert result is AppKeyEventResult.HANDLED_STOP


def test_command_dispatcher_returns_unhandled_without_active_flow() -> None:
    dispatcher = Access8GraphCommandDispatcher(
        translator=FakeTranslator({"key": "down", "repeat": 0, "pressing": 0}),
        navigation=FakeNavigationWithFlow(None),
    )

    result = dispatcher.handle_key_event(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.DOWN, pressed=True)
    )

    assert result is AppKeyEventResult.UNHANDLED


def test_command_dispatcher_sends_commands_to_active_flow() -> None:
    flow = RecordingFlow()
    command = {"key": "down", "repeat": 0, "pressing": 0}
    dispatcher = Access8GraphCommandDispatcher(
        translator=FakeTranslator(command),
        navigation=FakeNavigationWithFlow(flow),
    )

    result = dispatcher.handle_key_event(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.DOWN, pressed=True)
    )

    assert result is AppKeyEventResult.HANDLED_STOP
    assert flow.commands == [command]
```

- [ ] **Step 2: Run command dispatcher tests and verify they fail**

Run:

```bash
pytest tests/unit/test_access8graph_use_cases.py -k command_dispatcher -v
```

Expected: FAIL because `apps.access8graph.use_cases.command_dispatch` does not exist.

- [ ] **Step 3: Implement `Access8GraphCommandDispatcher`**

Create `src/apps/access8graph/use_cases/command_dispatch.py`:

```python
from application.input.results import AppKeyEventResult


class Access8GraphCommandDispatcher:
    def __init__(self, *, translator, navigation) -> None:
        self._translator = translator
        self._navigation = navigation

    def handle_key_event(self, event) -> AppKeyEventResult:
        command = self._translator.translate(event)
        if command is None:
            return AppKeyEventResult.HANDLED_STOP
        flow = self._navigation.current_flow
        if flow is None:
            return AppKeyEventResult.UNHANDLED
        flow.enter(command)
        return AppKeyEventResult.HANDLED_STOP
```

Update `src/apps/access8graph/use_cases/__init__.py`:

```python
from apps.access8graph.use_cases.command_dispatch import Access8GraphCommandDispatcher
from apps.access8graph.use_cases.graph_selection import GraphSelectionUseCase
from apps.access8graph.use_cases.navigation import (
    Access8GraphNavigationSession,
    MrtFlowFactory,
)

__all__ = [
    "Access8GraphCommandDispatcher",
    "Access8GraphNavigationSession",
    "GraphSelectionUseCase",
    "MrtFlowFactory",
]
```

- [ ] **Step 4: Run command dispatcher tests**

Run:

```bash
pytest tests/unit/test_access8graph_use_cases.py -k command_dispatcher -v
```

Expected: PASS.

- [ ] **Step 5: Rewire mode to use dispatcher**

In `src/apps/access8graph/service.py`, add `Access8GraphCommandDispatcher` to the use case import.

Add after navigation session creation:

```python
self._command_dispatcher = Access8GraphCommandDispatcher(
    translator=Access8GraphKeyTranslator(),
    navigation=self._navigation,
)
```

Replace `Access8GraphNavigationMode` with:

```python
class Access8GraphNavigationMode:
    mode_id = "navigation"
    enter_usage = HID.F10
    exit_usage = HID.ESCAPE

    def __init__(self, *, navigation, command_dispatcher):
        self._navigation = navigation
        self._command_dispatcher = command_dispatcher

    def can_enter(self) -> bool:
        return self._navigation.can_start()

    def enter(self) -> bool:
        self._navigation.start_flow()
        return True

    def exit(self) -> bool:
        self._navigation.stop_flow()
        return True

    def handle_key_event(self, event):
        return self._command_dispatcher.handle_key_event(event)
```

Update registration:

```python
self._mode_manager.register(
    Access8GraphNavigationMode(
        navigation=self._navigation,
        command_dispatcher=self._command_dispatcher,
    )
)
```

- [ ] **Step 6: Update failing flow dispatch test to patch through navigation**

In `tests/unit/test_access8graph_app_service.py`, replace direct `_flow` mutation in `test_service_stops_navigation_and_reports_flow_dispatch_exception` with:

```python
service._navigation._flow = FailingFlow()
```

This is a temporary white-box assertion for the current test. After this milestone, prefer new command dispatcher tests for flow dispatch behavior.

- [ ] **Step 7: Run Access8Graph tests**

Run:

```bash
pytest tests/unit/test_access8graph_input.py tests/unit/test_access8graph_use_cases.py tests/unit/test_access8graph_app_service.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit milestone 2**

```bash
git add src/apps/access8graph/use_cases src/apps/access8graph/service.py tests/unit/test_access8graph_use_cases.py tests/unit/test_access8graph_app_service.py
git commit -m "refactor: extract access8graph command dispatch boundary"
```

## Milestone 3: Shared Speech Settings Facade

### Task 4: Introduce Independent Speech Settings Facade

**Files:**
- Create: `src/apps/shared/speech_settings_facade.py`
- Modify: `src/apps/shared/__init__.py`
- Modify: `src/apps/shared/speech_settings_controller.py`
- Create: `tests/unit/test_speech_settings_facade.py`
- Modify: `tests/unit/test_speech_settings_controller.py`

- [ ] **Step 1: Copy controller tests to facade tests**

Create `tests/unit/test_speech_settings_facade.py` by copying the existing behavior from `tests/unit/test_speech_settings_controller.py`, changing imports and object names to:

```python
from apps.shared.speech_settings_facade import SpeechSettingsFacade
```

Use this representative construction in every copied test:

```python
facade = SpeechSettingsFacade(speech=speech)
```

For callback tests, use:

```python
facade = SpeechSettingsFacade(
    speech=speech,
    on_engine_changed=engine_changes.append,
    on_voice_changed=voice_changes.append,
    on_numeric_setting_changed=numeric_changes.append,
)
```

- [ ] **Step 2: Run facade tests and verify they fail**

Run:

```bash
pytest tests/unit/test_speech_settings_facade.py -v
```

Expected: FAIL because `apps.shared.speech_settings_facade` does not exist.

- [ ] **Step 3: Implement `SpeechSettingsFacade`**

Create `src/apps/shared/speech_settings_facade.py`:

```python
from collections.abc import Callable

from application.output import SpeechServiceProtocol


class SpeechSettingsFacade:
    def __init__(
        self,
        *,
        speech: SpeechServiceProtocol,
        on_engine_changed: Callable[[str], None] | None = None,
        on_voice_changed: Callable[[str, str], None] | None = None,
        on_numeric_setting_changed: Callable[[str, str, int], None] | None = None,
    ) -> None:
        self._speech = speech
        self._on_engine_changed = on_engine_changed
        self._on_voice_changed = on_voice_changed
        self._on_numeric_setting_changed = on_numeric_setting_changed

    def get_speech_engine_options(self) -> tuple[tuple[str, str], ...]:
        return self._speech.get_engine_options()

    def get_selected_speech_engine(self) -> str:
        return self._speech.get_selected_engine()

    def set_speech_engine(self, engine_id: str) -> None:
        self._speech.set_engine(engine_id)
        if self._on_engine_changed is not None:
            self._on_engine_changed(engine_id)

    def get_available_voices(self) -> tuple[tuple[str, str], ...]:
        return self._speech.list_voices()

    def get_selected_voice(self) -> str | None:
        return self._speech.get_voice()

    def set_selected_voice(self, voice_id: str) -> None:
        self._speech.set_voice(voice_id)
        if self._on_voice_changed is not None:
            self._on_voice_changed(self.get_selected_speech_engine(), voice_id)

    def get_rate(self) -> int | None:
        return self._speech.get_rate()

    def set_rate(self, value: int) -> None:
        self._speech.set_rate(value)
        if self._on_numeric_setting_changed is not None:
            self._on_numeric_setting_changed(
                self.get_selected_speech_engine(), "rate", value
            )

    def get_pitch(self) -> int | None:
        return self._speech.get_pitch()

    def set_pitch(self, value: int) -> None:
        self._speech.set_pitch(value)
        if self._on_numeric_setting_changed is not None:
            self._on_numeric_setting_changed(
                self.get_selected_speech_engine(), "pitch", value
            )

    def get_volume(self) -> int | None:
        return self._speech.get_volume()

    def set_volume(self, value: int) -> None:
        self._speech.set_volume(value)
        if self._on_numeric_setting_changed is not None:
            self._on_numeric_setting_changed(
                self.get_selected_speech_engine(), "volume", value
            )

    def get_supported_numeric_settings(self):
        return self._speech.get_supported_numeric_settings()
```

Update `src/apps/shared/speech_settings_controller.py` to preserve compatibility during the migration:

```python
from apps.shared.speech_settings_facade import SpeechSettingsFacade


class SpeechSettingsController(SpeechSettingsFacade):
    pass
```

Update `src/apps/shared/__init__.py`:

```python
from apps.shared.speech_settings_controller import SpeechSettingsController
from apps.shared.speech_settings_facade import SpeechSettingsFacade
from apps.shared.speech_runtime_settings import SpeechRuntimeSettingsCoordinator

__all__ = [
    "SpeechSettingsController",
    "SpeechSettingsFacade",
    "SpeechRuntimeSettingsCoordinator",
]
```

- [ ] **Step 4: Run shared speech settings tests**

Run:

```bash
pytest tests/unit/test_speech_settings_facade.py tests/unit/test_speech_settings_controller.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit facade introduction**

```bash
git add src/apps/shared/speech_settings_facade.py src/apps/shared/speech_settings_controller.py src/apps/shared/__init__.py tests/unit/test_speech_settings_facade.py tests/unit/test_speech_settings_controller.py
git commit -m "refactor: introduce shared speech settings facade"
```

### Task 5: Pass Speech Settings Facade Separately Through App Shells

**Files:**
- Modify: `src/apps/shared/tool_app_shell.py`
- Modify: `src/ui/nvda_remote/app.py`
- Modify: `src/ui/echo/app.py`
- Modify: `src/ui/access8graph/app.py`
- Modify: `src/apps/nvda_remote/main.py`
- Modify: `src/apps/key_echo/main.py`
- Modify: `src/apps/access8graph/main.py`
- Modify: `tests/unit/test_tool_app_shell.py`
- Modify: `tests/unit/test_app_wx.py`

- [ ] **Step 1: Add failing shell test for separate speech controller**

Add or update a test in `tests/unit/test_tool_app_shell.py`:

```python
def test_tool_app_shell_passes_separate_speech_controller_to_speech_frame(monkeypatch):
    import wx
    from apps.shared.tool_app_shell import ToolAppShell

    shown = []
    main_controller = object()
    speech_controller = object()
    received = {}

    class FakePanelController:
        def register(self, name, frame):
            received[name] = frame

        def show(self, name):
            shown.append(name)

    class FakeTrayIcon:
        def __init__(self, **kwargs):
            received["tray_kwargs"] = kwargs

        def Destroy(self):
            received["destroyed"] = True

    monkeypatch.setattr("apps.shared.tool_app_shell.PanelController", FakePanelController)
    monkeypatch.setattr("apps.shared.tool_app_shell.ToolTrayIcon", FakeTrayIcon)

    shell = ToolAppShell(
        controller=main_controller,
        speech_controller=speech_controller,
        main_frame_factory=lambda ctrl: ("main", ctrl),
        speech_frame_factory=lambda ctrl: ("speech", ctrl),
        app_name="Test",
    )

    shell.initialize()

    assert received["main"] == ("main", main_controller)
    assert received["speech"] == ("speech", speech_controller)
    assert shown == ["main"]
```

- [ ] **Step 2: Run shell test and verify it fails**

Run:

```bash
pytest tests/unit/test_tool_app_shell.py -k separate_speech_controller -v
```

Expected: FAIL because `ToolAppShell.__init__` does not accept `speech_controller`.

- [ ] **Step 3: Update `ToolAppShell`**

Modify `src/apps/shared/tool_app_shell.py`:

```python
class ToolAppShell:
    def __init__(
        self,
        *,
        controller,
        main_frame_factory,
        speech_frame_factory,
        speech_controller=None,
        app_name="NVDA Remote",
    ):
        self.controller = controller
        self.speech_controller = speech_controller if speech_controller is not None else controller
        self.main_frame_factory = main_frame_factory
        self.speech_frame_factory = speech_frame_factory
        self.app_name = app_name
        self.panel_controller = PanelController()
        self.tray_icon = None

    def initialize(self):
        if self.tray_icon is not None:
            return
        main_frame = self.main_frame_factory(self.controller)
        speech_frame = self.speech_frame_factory(self.speech_controller)
        self.panel_controller.register("main", main_frame)
        self.panel_controller.register("speech", speech_frame)
        self.tray_icon = ToolTrayIcon(
            on_open_main=lambda: self.panel_controller.show("main"),
            on_open_speech=lambda: self.panel_controller.show("speech"),
            on_exit=self.shutdown,
            app_name=self.app_name,
        )
        self.panel_controller.show("main")
```

Keep `shutdown()` unchanged so the main app service remains the shutdown owner.

- [ ] **Step 4: Update app classes to accept `speech_controller`**

In each of `src/ui/nvda_remote/app.py`, `src/ui/echo/app.py`, and `src/ui/access8graph/app.py`, change constructors to:

```python
def __init__(self, controller, speech_controller=None):
    self.controller = controller
    self.speech_controller = speech_controller if speech_controller is not None else controller
    super().__init__(False)
```

Pass `speech_controller=self.speech_controller` into `ToolAppShell`.

Example for `src/ui/access8graph/app.py`:

```python
self.shell = ToolAppShell(
    controller=self.controller,
    speech_controller=self.speech_controller,
    main_frame_factory=lambda ctrl: Access8GraphMainFrame(controller=ctrl),
    speech_frame_factory=lambda ctrl: SpeechSettingsFrame(controller=ctrl),
    app_name="Access8Graph",
)
```

- [ ] **Step 5: Build speech settings facades in app entrypoints**

In each app `main.py`, import:

```python
from apps.shared.speech_settings_facade import SpeechSettingsFacade
```

Create `speech_settings` after `on_speech_engine_changed`:

```python
speech_settings = SpeechSettingsFacade(
    speech=parts.output.speech,
    on_engine_changed=on_speech_engine_changed,
    on_voice_changed=config_store.save_voice,
    on_numeric_setting_changed=config_store.save_numeric_setting,
)
```

Pass `speech_controller=speech_settings` into the app constructor:

```python
app = Access8GraphApp(
    controller=app_service,
    speech_controller=speech_settings,
)
```

Apply the same pattern for `NvdaRemoteApp` and `EchoApp`.

- [ ] **Step 6: Keep app services compiling during transition**

Leave existing `SpeechSettingsController` construction and pass-through methods inside app services for this task. This keeps the runtime behavior stable while UI wiring moves to the facade.

- [ ] **Step 7: Run shell and wx tests**

Run:

```bash
pytest tests/unit/test_tool_app_shell.py tests/unit/test_app_wx.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit shell and app wiring**

```bash
git add src/apps/shared/tool_app_shell.py src/ui/nvda_remote/app.py src/ui/echo/app.py src/ui/access8graph/app.py src/apps/nvda_remote/main.py src/apps/key_echo/main.py src/apps/access8graph/main.py tests/unit/test_tool_app_shell.py tests/unit/test_app_wx.py
git commit -m "refactor: pass speech settings facade separately to ui"
```

### Task 6: Remove Speech Settings Pass-Through From App Services

**Files:**
- Modify: `src/apps/nvda_remote/service.py`
- Modify: `src/apps/key_echo/service.py`
- Modify: `src/apps/access8graph/service.py`
- Modify: `src/apps/nvda_remote/main.py`
- Modify: `src/apps/key_echo/main.py`
- Modify: `src/apps/access8graph/main.py`
- Modify: `tests/unit/test_nvda_remote_app_service.py`
- Modify: `tests/unit/test_key_echo_app_service.py`
- Modify: `tests/unit/test_access8graph_app_service.py`
- Modify: `tests/unit/test_app_wx.py`

- [ ] **Step 1: Update app service tests to stop asserting speech settings API**

Remove or rewrite tests whose only purpose is to assert speech settings pass-through methods on app services, including:

```python
test_key_echo_app_service_exposes_speech_settings_api
```

For `NvdaRemoteAppService` and `Access8GraphAppService`, replace direct service speech settings assertions with facade tests in `tests/unit/test_speech_settings_facade.py`.

- [ ] **Step 2: Remove `SpeechSettingsController` construction from services**

In each app service, remove:

```python
from apps.shared.speech_settings_controller import SpeechSettingsController
```

Remove constructor parameters that only exist for speech settings callbacks:

```python
on_speech_engine_changed: Callable[[str], None] | None = None,
on_voice_changed: Callable[[str, str], None] | None = None,
on_numeric_setting_changed: Callable[[str, str, int], None] | None = None,
```

Remove this construction:

```python
self._speech_settings = SpeechSettingsController(...)
```

- [ ] **Step 3: Remove speech settings pass-through methods from services**

Delete these methods from `src/apps/nvda_remote/service.py`, `src/apps/key_echo/service.py`, and `src/apps/access8graph/service.py`:

```python
def get_speech_engine_options(self) -> tuple[tuple[str, str], ...]: ...
def get_selected_speech_engine(self) -> str: ...
def set_speech_engine(self, engine_id: str) -> None: ...
def get_supported_numeric_settings(self): ...
def get_available_voices(self) -> tuple[tuple[str, str], ...]: ...
def get_selected_voice(self) -> str | None: ...
def set_selected_voice(self, voice_id: str) -> None: ...
def get_rate(self) -> int | None: ...
def set_rate(self, value: int) -> None: ...
def get_pitch(self) -> int | None: ...
def set_pitch(self, value: int) -> None: ...
def get_volume(self) -> int | None: ...
def set_volume(self, value: int) -> None: ...
```

- [ ] **Step 4: Preserve speech engine status events in facade callbacks**

Where an app previously emitted `SpeechEngineChanged` from service `set_speech_engine`, wrap the facade callback in `main.py`.

For each app, create:

```python
def _notify_speech_engine_changed(engine_id: str) -> None:
    on_speech_engine_changed(engine_id)
    app_service._notify_status_listener(SpeechEngineChanged(engine_id))
```

If using a private service notifier feels too leaky during implementation, add a small public method to each app service:

```python
def notify_speech_engine_changed(self, engine_id: str) -> None:
    self._notify_status_listener(SpeechEngineChanged(engine_id))
```

Then pass:

```python
speech_settings = SpeechSettingsFacade(
    speech=parts.output.speech,
    on_engine_changed=lambda engine_id: (
        on_speech_engine_changed(engine_id),
        app_service.notify_speech_engine_changed(engine_id),
    ),
    on_voice_changed=config_store.save_voice,
    on_numeric_setting_changed=config_store.save_numeric_setting,
)
```

Use a named function instead of a tuple-returning lambda in final code:

```python
def _on_engine_changed(engine_id: str) -> None:
    on_speech_engine_changed(engine_id)
    app_service.notify_speech_engine_changed(engine_id)
```

- [ ] **Step 5: Run targeted speech and app tests**

Run:

```bash
pytest tests/unit/test_speech_settings_facade.py tests/unit/test_app_wx.py tests/unit/test_nvda_remote_app_service.py tests/unit/test_key_echo_app_service.py tests/unit/test_access8graph_app_service.py -v
```

Expected: PASS.

- [ ] **Step 6: Search for remaining app service speech settings calls**

Run:

```bash
rg "get_speech_engine_options|get_selected_speech_engine|set_speech_engine|get_available_voices|get_selected_voice|set_selected_voice|get_rate|set_rate|get_pitch|set_pitch|get_volume|set_volume" src tests -n
```

Expected: remaining references should be in `SpeechSettingsFacade`, `SpeechControlsMixin`, facade tests, and UI fakes only. They should not be methods on app service classes.

- [ ] **Step 7: Commit service surface reduction**

```bash
git add src/apps/nvda_remote/service.py src/apps/key_echo/service.py src/apps/access8graph/service.py src/apps/nvda_remote/main.py src/apps/key_echo/main.py src/apps/access8graph/main.py tests/unit/test_nvda_remote_app_service.py tests/unit/test_key_echo_app_service.py tests/unit/test_access8graph_app_service.py tests/unit/test_app_wx.py
git commit -m "refactor: move speech settings out of app services"
```

## Milestone 4: Remove `application.output.Manager`

### Task 7: Move `ClipboardService` Protocol Out Of Manager Module

**Files:**
- Create: `src/application/output/clipboard.py`
- Modify: `src/application/output/__init__.py`
- Modify: `tests/unit/test_output_service.py`

- [ ] **Step 1: Add failing import/export test**

In `tests/unit/test_output_service.py`, replace any assertion that imports `Manager` with:

```python
def test_application_output_exports_clipboard_service_protocol():
    from application.output import ClipboardService

    assert ClipboardService is not None
```

- [ ] **Step 2: Run output export test**

Run:

```bash
pytest tests/unit/test_output_service.py -k clipboard_service_protocol -v
```

Expected: PASS before deletion if `ClipboardService` is still re-exported from `manager.py`.

- [ ] **Step 3: Create new clipboard protocol module**

Create `src/application/output/clipboard.py`:

```python
from typing import Protocol


class ClipboardService(Protocol):
    def set_text(self, text: str) -> None: ...

    def get_text(self) -> str: ...
```

Update `src/application/output/__init__.py` so it imports `ClipboardService` from the new module:

```python
from application.output.clipboard import ClipboardService
```

Keep `Manager` exported for this task only.

- [ ] **Step 4: Update direct clipboard imports if needed**

Search:

```bash
rg "application.output.manager import ClipboardService|from application.output import ClipboardService" src tests -n
```

Keep `from application.output import ClipboardService` call sites unchanged. Replace direct `application.output.manager import ClipboardService` imports with:

```python
from application.output import ClipboardService
```

- [ ] **Step 5: Run output and bootstrap tests**

Run:

```bash
pytest tests/unit/test_output_service.py tests/unit/test_bootstrap_platform.py tests/unit/test_bootstrap_app_runtime.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit clipboard protocol move**

```bash
git add src/application/output/clipboard.py src/application/output/__init__.py tests/unit/test_output_service.py
git commit -m "refactor: move clipboard protocol out of output manager"
```

### Task 8: Remove Manager Usage From Tests And Production Exports

**Files:**
- Delete: `src/application/output/manager.py`
- Modify: `src/application/output/__init__.py`
- Modify: `tests/unit/test_message_router.py`
- Modify: `tests/unit/test_speech_backends.py`
- Delete or Rewrite: `tests/unit/test_output_manager.py`
- Modify: `tests/unit/test_output_service.py`

- [ ] **Step 1: Replace `Manager` usage in message router tests**

In `tests/unit/test_message_router.py`, replace imports:

```python
from application.output import Manager
```

with local fakes:

```python
class RecordingSpeech:
    def __init__(self) -> None:
        self.spoken = []
        self.cancel_count = 0
        self.pauses = []

    def speak(self, sequence) -> None:
        self.spoken.append(sequence)

    def cancel(self) -> None:
        self.cancel_count += 1

    def pause(self, is_paused: bool) -> None:
        self.pauses.append(is_paused)


class RecordingClipboard:
    def __init__(self) -> None:
        self.text = None

    def set_text(self, text: str) -> None:
        self.text = text


class RecordingTone:
    def __init__(self) -> None:
        self.calls = []

    def beep(self, hz: float, length: int, left: int = 50, right: int = 50) -> None:
        self.calls.append((hz, length, left, right))
```

When constructing `MessageRouter`, pass explicit callbacks:

```python
speech = RecordingSpeech()
clipboard = RecordingClipboard()
tone = RecordingTone()
router = MessageRouter(
    on_speech=speech.speak,
    on_cancel=speech.cancel,
    on_pause=speech.pause,
    on_clipboard=clipboard.set_text,
    on_tone=tone.beep,
    on_status=statuses.append,
)
```

- [ ] **Step 2: Replace `Manager` usage in speech backend tests**

In `tests/unit/test_speech_backends.py`, replace tests that use `Manager` only to call `handle_speech`, `handle_cancel`, or `set_speech_output`.

Use direct output calls:

```python
output.speak(sequence)
output.cancel()
```

For speech output replacement behavior, keep that behavior only if it belongs to a surviving class. If the only owner was `Manager`, remove that test because the wrapper behavior is being retired.

- [ ] **Step 3: Remove manager export and module**

Update `src/application/output/__init__.py`:

```python
from application.output.capabilities import Capabilities
from application.output.clipboard import ClipboardService
from application.output.scheduler import (
    CancellationToken,
    EventCallbacks,
    ScheduledFuture,
    Scheduler,
)
from application.output.service import Mode, QueuedService, SpeechServiceProtocol

__all__ = [
    "CancellationToken",
    "ClipboardService",
    "Capabilities",
    "EventCallbacks",
    "ScheduledFuture",
    "Mode",
    "Scheduler",
    "QueuedService",
    "SpeechServiceProtocol",
]
```

Delete `src/application/output/manager.py`.

- [ ] **Step 4: Delete wrapper-only manager tests**

Delete `tests/unit/test_output_manager.py` if all remaining assertions only verify `Manager` forwarding behavior.

If any assertion protects behavior still present elsewhere, move it to the test for that surviving class. For example, message router tone routing belongs in `tests/unit/test_message_router.py`, not in a manager test.

- [ ] **Step 5: Update output service export tests**

In `tests/unit/test_output_service.py`, remove assertions that `Manager` is exported. Keep assertions for `ClipboardService`, `Capabilities`, `QueuedService`, `Scheduler`, and `SpeechServiceProtocol`.

- [ ] **Step 6: Search for remaining manager references**

Run:

```bash
rg "\\bManager\\b|application.output.manager" src tests -n
```

Expected: no references to `application.output.Manager` or `application.output.manager`. If `Manager` appears in unrelated prose or local variable names, rename those references for clarity.

- [ ] **Step 7: Run output and router tests**

Run:

```bash
pytest tests/unit/test_output_service.py tests/unit/test_message_router.py tests/unit/test_speech_backends.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit manager removal**

```bash
git add src/application/output/__init__.py src/application/output/clipboard.py tests/unit/test_output_service.py tests/unit/test_message_router.py tests/unit/test_speech_backends.py
git rm src/application/output/manager.py tests/unit/test_output_manager.py
git commit -m "refactor: remove output manager"
```

## Final Verification

- [ ] **Step 1: Run Access8Graph-focused tests**

Run:

```bash
pytest tests/unit/test_access8graph_input.py tests/unit/test_access8graph_flow.py tests/unit/test_access8graph_use_cases.py tests/unit/test_access8graph_app_service.py tests/unit/test_access8graph_ui.py tests/integration/test_access8graph_mrt_flow.py -v
```

Expected: PASS.

- [ ] **Step 2: Run shared speech settings and UI shell tests**

Run:

```bash
pytest tests/unit/test_speech_settings_facade.py tests/unit/test_speech_settings_controller.py tests/unit/test_tool_app_shell.py tests/unit/test_app_wx.py -v
```

Expected: PASS.

- [ ] **Step 3: Run output and protocol routing tests**

Run:

```bash
pytest tests/unit/test_output_service.py tests/unit/test_message_router.py tests/unit/test_speech_backends.py -v
```

Expected: PASS.

- [ ] **Step 4: Run the full suite**

Run:

```bash
pytest tests/unit tests/integration -v
```

Expected: PASS.

- [ ] **Step 5: Confirm architectural cleanup searches**

Run:

```bash
rg "_start_flow|_stop_flow|application.output.manager|\\bManager\\b" src tests -n
```

Expected:

- no `Access8GraphAppService._start_flow`
- no `Access8GraphAppService._stop_flow`
- no import or usage of `application.output.manager`
- no `Manager` symbol referring to the retired output manager

Run:

```bash
rg "def get_speech_engine_options|def set_speech_engine|def get_available_voices|def set_selected_voice|def set_rate|def set_pitch|def set_volume" src/apps -n
```

Expected: these methods exist on `SpeechSettingsFacade` or compatibility wrapper only, not on app service classes.

## Self-Review Notes

- Spec coverage: Milestone 1 is covered by Tasks 1 and 2, Milestone 2 by Task 3, Milestone 3 by Tasks 4 through 6, and Milestone 4 by Tasks 7 and 8.
- Placeholder scan: The plan intentionally avoids open-ended steps and provides exact target paths, commands, and code blocks for new files and key modified methods.
- Type consistency: The plan uses `GraphSelectionUseCase`, `Access8GraphNavigationSession`, `MrtFlowFactory`, `Access8GraphCommandDispatcher`, and `SpeechSettingsFacade` consistently across tests, implementation, and wiring.
