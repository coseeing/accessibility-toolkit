# Application Boundaries and Access8Graph Transition Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct the remaining package boundaries and replace the Access8Graph State hierarchy with a fixed-target declarative transition engine while preserving all observable behavior.

**Architecture:** Complete low-risk ownership and dependency-inversion work first, then capture the existing Access8Graph behavior as characterization scenarios. Build a typed transition engine beside the legacy flow, prove parity, switch production atomically, and finally split stable transition/action modules by navigation concern.

**Tech Stack:** Python 3.11+, pytest, `dataclasses`, `enum.StrEnum`, structural `Protocol` typing, existing wxPython UI, existing Access8Graph GraphML navigators

---

## Source Design

Implement from:

- `docs/superpowers/specs/2026-06-27-application-boundaries-and-access8graph-transition-engine-design.md`

The Traditional Chinese translation is reference-only:

- `docs/superpowers/specs/2026-06-27-application-boundaries-and-access8graph-transition-engine-design_ZH-TW.md`

If the two documents differ, the English design is authoritative.

## Execution Rules

- Run the smallest relevant test first, then the milestone suite.
- Follow red-green-refactor for every behavioral change.
- Use exact-path `git add`; the worktree may contain unrelated documentation.
- Do not change the GraphML model/navigator, scheduler, bootstrap behavior, UI
  behavior, or speech-settings JSON schema.
- Do not fix behavior discovered by characterization tests unless a separate
  approved task is added.
- Complete and review each milestone before starting the next.

## File Structure

| File | Responsibility |
|---|---|
| `src/application/input/service.py` | Canonical keyboard input service and handler protocol |
| `src/application/output/ports.py` | Narrow output, settings, lifecycle, and composite speech protocols |
| `src/application/output/speech/settings_store.py` | Application-level speech settings persistence port |
| `src/adapters/config/json_speech_settings.py` | JSON/filesystem implementation of the persistence port |
| `src/apps/nvda_remote/state.py` | NVDA Remote-only runtime state |
| `src/ui/shared/panel_controller.py` | Shared wx frame visibility coordination |
| `src/ui/shared/tool_app_shell.py` | Shared wx app shell |
| `src/ui/shared/tray_icon.py` | Shared wx tray icon |
| `tests/unit/access8graph_flow_scenarios.py` | Shared legacy/new flow scenario definitions and fakes |
| `tests/unit/test_access8graph_flow_characterization.py` | Legacy observable-behavior baseline |
| `src/apps/access8graph/navigation/model.py` | Commands, state IDs, context, rule/result/effect value objects |
| `src/apps/access8graph/navigation/snapshot.py` | Immutable snapshot construction and pure guard inputs |
| `src/apps/access8graph/navigation/engine.py` | Rule selection, action execution, state commit, and AUTO macrosteps |
| `src/apps/access8graph/navigation/actions.py` | Initial consolidated guards, actions, and lifecycle handlers |
| `src/apps/access8graph/navigation/table.py` | Initial complete fixed-target transition table and validator |
| `src/apps/access8graph/navigation/presenter.py` | Ordered macrostep presentation and output policy |
| `src/apps/access8graph/navigation/flow.py` | Flow adapter composed from engine, table, handlers, and presenter |
| `tests/unit/test_access8graph_navigation_model.py` | Enum and value-object contracts |
| `tests/unit/test_access8graph_transition_table.py` | Static and runtime transition-table validation |
| `tests/unit/test_access8graph_transition_engine.py` | Macrostep, ambiguity, commit, rejection, exception, and AUTO behavior |
| `tests/unit/test_access8graph_navigation_actions.py` | Guard, action, snapshot, and lifecycle behavior |
| `tests/unit/test_access8graph_flow_presenter.py` | Exact presentation ordering and output calls |
| `tests/unit/test_access8graph_transition_parity.py` | Legacy/new scenario parity |

After Milestone 5, `actions.py` and `table.py` become packages grouped by
navigation concern.

---

## Milestone 1: Low-Risk Boundary and Compatibility Cleanup

### Task 1: Finish and Verify the Keyboard Service Relocation

**Files:**
- Existing: `src/application/input/service.py`
- Modify: `src/application/input/__init__.py`
- Delete: `src/application/keyboard.py`
- Modify: `src/apps/access8graph/main.py`
- Modify: `src/apps/access8graph/service.py`
- Modify: `src/apps/key_echo/main.py`
- Modify: `src/apps/key_echo/service.py`
- Modify: `src/apps/nvda_remote/main.py`
- Modify: `src/apps/nvda_remote/service.py`
- Modify: `tests/unit/test_keyboard_input_service.py`
- Modify: `tests/unit/test_access8graph_app_service.py`
- Modify: `tests/unit/test_key_echo_app_service.py`

- [ ] **Step 1: Inspect the existing relocation diff**

Run:

```bash
git diff -- src/application/input src/application/keyboard.py src/apps tests/unit/test_keyboard_input_service.py tests/unit/test_access8graph_app_service.py tests/unit/test_key_echo_app_service.py
```

Expected: `KeyboardInputService` and `KeyEventHandler` are defined only in
`application.input.service`, exported from `application.input`, and all direct
consumers use the new import.

- [ ] **Step 2: Verify the old import is gone**

Run:

```bash
rg -n "application\.keyboard" src tests
```

Expected: no matches.

- [ ] **Step 3: Run focused tests**

Run:

```bash
pytest tests/unit/test_keyboard_input_service.py tests/unit/test_access8graph_app_service.py tests/unit/test_key_echo_app_service.py tests/unit/test_nvda_remote_app_service.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit the relocation**

```bash
git add src/application/input/service.py src/application/input/__init__.py src/application/keyboard.py src/apps/access8graph/main.py src/apps/access8graph/service.py src/apps/key_echo/main.py src/apps/key_echo/service.py src/apps/nvda_remote/main.py src/apps/nvda_remote/service.py tests/unit/test_keyboard_input_service.py tests/unit/test_access8graph_app_service.py tests/unit/test_key_echo_app_service.py
git commit -m "refactor: move keyboard service into application input"
```

### Task 2: Introduce the Speech Settings Store Port and JSON Adapter

**Files:**
- Create: `src/application/output/speech/settings_store.py`
- Create: `src/adapters/config/__init__.py`
- Create: `src/adapters/config/json_speech_settings.py`
- Create: `tests/unit/test_json_speech_settings_store.py`
- Modify: `src/apps/shared/speech_runtime_settings.py`
- Modify: `src/apps/access8graph/main.py`
- Modify: `src/apps/key_echo/main.py`
- Modify: `src/apps/nvda_remote/main.py`
- Modify: `tests/unit/test_speech_runtime_settings.py`
- Modify: `tests/integration/test_speech_engine_persistence_and_routing.py`
- Delete: `src/application/config.py`

- [ ] **Step 1: Write the port and adapter contract tests**

Create tests covering missing files, malformed JSON, engine persistence,
per-engine voice persistence, numeric clamping, and preservation of unrelated
keys:

```python
from __future__ import annotations

import json

from adapters.config.json_speech_settings import JsonSpeechSettingsStore


def test_missing_file_returns_defaults(tmp_path):
    store = JsonSpeechSettingsStore(tmp_path / "settings.json")

    assert store.load_engine_id(default_engine_id="Pyttsx3") == "Pyttsx3"
    assert store.load_voice("Pyttsx3") is None
    assert store.load_numeric_setting("Pyttsx3", "rate") is None


def test_malformed_file_returns_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{bad", encoding="utf-8")
    store = JsonSpeechSettingsStore(path)

    assert store.load_engine_id(default_engine_id="NVDA") == "NVDA"


def test_store_preserves_schema_and_unrelated_keys(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"other": {"enabled": True}}), encoding="utf-8")
    store = JsonSpeechSettingsStore(path)

    store.save_engine_id("Pyttsx3")
    store.save_voice("Pyttsx3", "voice-1")
    store.save_numeric_setting("Pyttsx3", "rate", 140)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload == {
        "other": {"enabled": True},
        "speech_engine": "Pyttsx3",
        "speech_engines": {
            "Pyttsx3": {
                "voice": "voice-1",
                "rate": 100,
            }
        },
    }
```

- [ ] **Step 2: Run the new tests and verify they fail**

Run:

```bash
pytest tests/unit/test_json_speech_settings_store.py -q
```

Expected: FAIL because `adapters.config.json_speech_settings` does not exist.

- [ ] **Step 3: Define the application port**

```python
from typing import Protocol


class SpeechSettingsStore(Protocol):
    def load_engine_id(self, *, default_engine_id: str) -> str: ...
    def save_engine_id(self, engine_id: str) -> None: ...
    def load_voice(self, engine_id: str) -> str | None: ...
    def save_voice(self, engine_id: str, voice_id: str) -> None: ...
    def load_numeric_setting(
        self, engine_id: str, setting_id: str
    ) -> int | None: ...
    def save_numeric_setting(
        self, engine_id: str, setting_id: str, value: int
    ) -> None: ...
```

- [ ] **Step 4: Move the JSON implementation behind the port**

Move the behavior from `SpeechEngineConfigStore` into
`JsonSpeechSettingsStore`. Keep the same `_read`, `_write`,
`_engine_payload`, and `_ensure_engine_payload` semantics and import
`clamp_percent` from `application.output.speech.settings`.

- [ ] **Step 5: Run the adapter tests**

Run:

```bash
pytest tests/unit/test_json_speech_settings_store.py -q
```

Expected: PASS.

- [ ] **Step 6: Make the coordinator depend on the port**

Change the constructor to:

```python
from application.output.speech.settings_store import SpeechSettingsStore


class SpeechRuntimeSettingsCoordinator:
    def __init__(self, *, config_store: SpeechSettingsStore) -> None:
        self._config_store = config_store
```

Keep the public parameter name `config_store` to avoid unrelated runtime
wiring churn.

- [ ] **Step 7: Migrate runtime and tests to the adapter**

Replace every `SpeechEngineConfigStore` construction with:

```python
from adapters.config.json_speech_settings import JsonSpeechSettingsStore

config_store = JsonSpeechSettingsStore(default_config_path())
```

Use the same class in persistence integration tests.

- [ ] **Step 8: Delete the concrete application store and verify imports**

Delete `src/application/config.py`, then run:

```bash
rg -n "SpeechEngineConfigStore|application\.config" src tests
```

Expected: no matches.

- [ ] **Step 9: Run persistence tests**

Run:

```bash
pytest tests/unit/test_json_speech_settings_store.py tests/unit/test_speech_runtime_settings.py tests/unit/test_bootstrap_app_runtime.py tests/unit/test_speech_backends.py tests/integration/test_speech_engine_persistence_and_routing.py -q
```

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add src/application/output/speech/settings_store.py src/adapters/config/__init__.py src/adapters/config/json_speech_settings.py src/apps/shared/speech_runtime_settings.py src/apps/access8graph/main.py src/apps/key_echo/main.py src/apps/nvda_remote/main.py tests/unit/test_json_speech_settings_store.py tests/unit/test_speech_runtime_settings.py tests/unit/test_bootstrap_app_runtime.py tests/unit/test_speech_backends.py tests/integration/test_speech_engine_persistence_and_routing.py src/application/config.py
git commit -m "refactor: move speech settings persistence behind port"
```

### Task 3: Split the Speech Service Protocol by Consumer Role

**Files:**
- Create: `src/application/output/ports.py`
- Modify: `src/application/output/service.py`
- Modify: `src/application/output/capabilities.py`
- Modify: `src/application/output/__init__.py`
- Modify: `src/apps/shared/speech_settings_facade.py`
- Modify: `src/apps/access8graph/output.py`
- Modify: `src/apps/access8graph/service.py`
- Modify: `tests/unit/test_output_service.py`
- Create: `tests/unit/test_output_ports.py`

- [ ] **Step 1: Write structural protocol tests**

```python
from typing import runtime_checkable

from application.output.ports import (
    SpeechLifecyclePort,
    SpeechOutputPort,
    SpeechServicePort,
    SpeechSettingsPort,
)


class CompleteSpeech:
    def speak(self, sequence): pass
    def cancel(self): pass
    def pause(self, is_paused): pass
    def get_engine_options(self): return ()
    def get_selected_engine(self): return "fake"
    def set_engine(self, engine_id): pass
    def list_voices(self): return ()
    def get_voice(self): return None
    def set_voice(self, voice_id): pass
    def get_rate(self): return None
    def set_rate(self, value): pass
    def get_pitch(self): return None
    def set_pitch(self, value): pass
    def get_volume(self): return None
    def set_volume(self, value): pass
    def get_supported_numeric_settings(self): return ()
    def shutdown(self): pass


def test_complete_speech_satisfies_all_ports():
    speech = CompleteSpeech()

    assert isinstance(speech, SpeechOutputPort)
    assert isinstance(speech, SpeechSettingsPort)
    assert isinstance(speech, SpeechLifecyclePort)
    assert isinstance(speech, SpeechServicePort)
```

Decorate all four protocols with `@runtime_checkable`.

- [ ] **Step 2: Run the protocol test and verify it fails**

Run:

```bash
pytest tests/unit/test_output_ports.py -q
```

Expected: FAIL because `application.output.ports` does not exist.

- [ ] **Step 3: Implement the four protocols**

Implement the exact signatures from the approved design. Import
`SpeechNumericSetting` and `SpeechSequence` only under `TYPE_CHECKING` where
runtime imports would create a cycle.

- [ ] **Step 4: Replace the broad protocol**

- `Capabilities.speech` uses `SpeechServicePort`.
- `SpeechSettingsFacade` accepts `SpeechSettingsPort`.
- `Access8GraphFlowOutput` accepts `SpeechOutputPort` and optional `ToneOutput`
  directly; its app service passes `capabilities.speech` and
  `capabilities.tone`.
- remove `SpeechServiceProtocol` from `application.output.service` and package
  exports.

- [ ] **Step 5: Verify the removed name**

Run:

```bash
rg -n "SpeechServiceProtocol" src tests
```

Expected: no matches.

- [ ] **Step 6: Run output and app-service tests**

Run:

```bash
pytest tests/unit/test_output_ports.py tests/unit/test_output_service.py tests/unit/test_speech_service.py tests/unit/test_speech_settings_facade.py tests/unit/test_access8graph_output.py tests/unit/test_access8graph_app_service.py tests/unit/test_key_echo_app_service.py tests/unit/test_nvda_remote_app_service.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/application/output/ports.py src/application/output/service.py src/application/output/capabilities.py src/application/output/__init__.py src/apps/shared/speech_settings_facade.py src/apps/access8graph/output.py src/apps/access8graph/service.py tests/unit/test_output_ports.py tests/unit/test_output_service.py tests/unit/test_speech_service.py tests/unit/test_speech_settings_facade.py tests/unit/test_access8graph_output.py tests/unit/test_access8graph_app_service.py tests/unit/test_key_echo_app_service.py tests/unit/test_nvda_remote_app_service.py
git commit -m "refactor: split speech service ports by consumer"
```

### Task 4: Remove Speech Settings Aliases and Move NVDA Remote State

**Files:**
- Create: `src/apps/nvda_remote/state.py`
- Modify: `src/apps/nvda_remote/service.py`
- Modify: `src/apps/nvda_remote/use_cases/connection.py`
- Modify: `src/apps/nvda_remote/use_cases/control_mode.py`
- Modify: `src/apps/nvda_remote/use_cases/__init__.py`
- Modify: `src/apps/key_echo/use_cases/__init__.py`
- Modify: `src/apps/shared/__init__.py`
- Modify: `tests/unit/test_nvda_remote_use_cases.py`
- Modify: `tests/unit/test_nvda_remote_app_service.py`
- Modify: `tests/unit/test_key_echo_use_cases.py`
- Modify: `tests/unit/test_speech_settings_facade.py`
- Delete: `src/application/state.py`
- Delete: `src/apps/shared/speech_settings_controller.py`
- Delete: `src/apps/key_echo/use_cases/speech_settings.py`
- Delete: `src/apps/nvda_remote/use_cases/speech_settings.py`
- Delete or rename: `tests/unit/test_speech_settings_controller.py`

- [ ] **Step 1: Move state contract tests to the app package**

Update NVDA Remote use-case tests to import:

```python
from apps.nvda_remote.state import ConnectionState, ControlState, RuntimeState
```

Run:

```bash
pytest tests/unit/test_nvda_remote_use_cases.py -q
```

Expected: FAIL because `apps.nvda_remote.state` does not exist.

- [ ] **Step 2: Create the NVDA Remote state module**

Move the three existing types without behavior changes:

```python
from dataclasses import dataclass
from enum import StrEnum


class ConnectionState(StrEnum):
    IDLE = "idle"
    CONNECTED = "connected"


class ControlState(StrEnum):
    IDLE = "idle"
    CONNECTED = "connected"
    CONTROLLING = "controlling"
    SUSPENDED = "suspended"


@dataclass(slots=True)
class RuntimeState:
    connection_state: ConnectionState | str = ConnectionState.IDLE
    control_state: ControlState | str = ControlState.IDLE
```

- [ ] **Step 3: Migrate state imports and delete the old module**

Update all production and test imports, delete `application/state.py`, and run:

```bash
rg -n "application\.state" src tests
```

Expected: no matches.

- [ ] **Step 4: Replace alias tests with facade tests**

Move any unique callback and proxy assertions from
`test_speech_settings_controller.py` into
`test_speech_settings_facade.py`. Delete tests whose only purpose is proving
that an alias subclasses or re-exports the facade.

- [ ] **Step 5: Delete compatibility modules and exports**

Delete the three alias modules, remove their package exports, and run:

```bash
rg -n "SpeechSettingsController|KeyEchoSpeechSettingsUseCase|NvdaRemoteSpeechSettingsUseCase|speech_settings_controller|use_cases\.speech_settings" src tests
```

Expected: no matches.

- [ ] **Step 6: Run focused tests**

Run:

```bash
pytest tests/unit/test_nvda_remote_use_cases.py tests/unit/test_nvda_remote_app_service.py tests/unit/test_key_echo_use_cases.py tests/unit/test_speech_settings_facade.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/apps/nvda_remote/state.py src/apps/nvda_remote/service.py src/apps/nvda_remote/use_cases/__init__.py src/apps/nvda_remote/use_cases/connection.py src/apps/nvda_remote/use_cases/control_mode.py src/apps/nvda_remote/use_cases/speech_settings.py src/apps/key_echo/use_cases/__init__.py src/apps/key_echo/use_cases/speech_settings.py src/apps/shared/__init__.py src/apps/shared/speech_settings_controller.py src/application/state.py tests/unit/test_nvda_remote_use_cases.py tests/unit/test_nvda_remote_app_service.py tests/unit/test_key_echo_use_cases.py tests/unit/test_speech_settings_facade.py tests/unit/test_speech_settings_controller.py
git commit -m "refactor: remove speech aliases and localize remote state"
```

### Task 5: Move wx Shell Components into `ui.shared`

**Files:**
- Create: `src/ui/shared/panel_controller.py`
- Create: `src/ui/shared/tool_app_shell.py`
- Create: `src/ui/shared/tray_icon.py`
- Modify: `src/ui/shared/__init__.py`
- Modify: `src/ui/access8graph/app.py`
- Modify: `src/ui/echo/app.py`
- Modify: `src/ui/nvda_remote/app.py`
- Modify: `tests/unit/test_panel_controller.py`
- Modify: `tests/unit/test_tool_app_shell.py`
- Modify: `tests/unit/test_tray_icon.py`
- Modify: `tests/unit/test_app_wx.py`
- Modify: `tests/unit/test_access8graph_ui.py`
- Delete: corresponding files under `src/apps/shared/`

- [ ] **Step 1: Change tests to the target imports**

Use:

```python
from ui.shared.panel_controller import PanelController
from ui.shared.tool_app_shell import ToolAppShell
from ui.shared.tray_icon import ToolTrayIcon
```

Update monkeypatch paths to `ui.shared.tool_app_shell`.

- [ ] **Step 2: Run focused tests and verify they fail**

Run:

```bash
pytest tests/unit/test_panel_controller.py tests/unit/test_tool_app_shell.py tests/unit/test_tray_icon.py -q
```

Expected: FAIL because the target modules do not exist.

- [ ] **Step 3: Move the modules without behavior changes**

Preserve class names, constructor signatures, callback ordering, panel IDs, and
wx event bindings exactly. Update imports within `tool_app_shell.py` to use
`ui.shared`.

- [ ] **Step 4: Update UI app imports and delete old modules**

Update the three app wrappers, delete old modules, and run:

```bash
rg -n "apps\.shared\.(panel_controller|tool_app_shell|tray_icon)" src tests
```

Expected: no matches.

- [ ] **Step 5: Run wx tests**

Run:

```bash
pytest tests/unit/test_panel_controller.py tests/unit/test_tool_app_shell.py tests/unit/test_tray_icon.py tests/unit/test_app_wx.py tests/unit/test_access8graph_ui.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/ui/shared/__init__.py src/ui/shared/panel_controller.py src/ui/shared/tool_app_shell.py src/ui/shared/tray_icon.py src/ui/access8graph/app.py src/ui/echo/app.py src/ui/nvda_remote/app.py src/apps/shared/panel_controller.py src/apps/shared/tool_app_shell.py src/apps/shared/tray_icon.py tests/unit/test_panel_controller.py tests/unit/test_tool_app_shell.py tests/unit/test_tray_icon.py tests/unit/test_app_wx.py tests/unit/test_access8graph_ui.py
git commit -m "refactor: move shared wx shell into ui package"
```

### Task 6: Milestone 1 Verification

- [ ] **Step 1: Verify removed paths**

Run:

```bash
rg -n "application\.keyboard|application\.config|application\.state|SpeechServiceProtocol|SpeechSettingsController|apps\.shared\.(panel_controller|tool_app_shell|tray_icon)" src tests
```

Expected: no matches.

- [ ] **Step 2: Run the full suite**

Run:

```bash
pytest tests/unit tests/integration -q
```

Expected: PASS.

- [ ] **Step 3: Record the milestone**

```bash
git status --short
git log -5 --oneline
```

Expected: no uncommitted source/test changes from Milestone 1; unrelated user
documentation may remain.

---

## Milestone 2: Existing Flow Behavior Baseline

### Task 7: Build the Characterization Scenario Harness

**Files:**
- Create: `tests/unit/access8graph_flow_scenarios.py`
- Create: `tests/unit/test_access8graph_flow_characterization.py`
- Modify: `tests/unit/test_access8graph_flow.py`

- [ ] **Step 1: Define observable trace types**

```python
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True, slots=True)
class OutputCall:
    kind: str
    payload: tuple[object, ...] = ()


@dataclass(frozen=True, slots=True)
class FlowTrace:
    state_id: str
    background_state_id: str | None
    output_calls: tuple[OutputCall, ...]
    direction: dict[str, Any]
    undirection: dict[str, Any]


@dataclass(frozen=True, slots=True)
class FlowScenario:
    id: str
    start_state: str
    command: str
    arrange: Callable[[object], None]
    expected_state: str
    expected_success: bool
    expected_beep: bool = False
```

Add `RecordingOutput`, complete fake direction/undirected navigators, a
`build_legacy_flow()` helper, and `capture_legacy_trace()`.

- [ ] **Step 2: Add the state manifest**

Define the exact expected legacy state IDs:

```python
LEGACY_STATE_IDS = {
    "mode",
    "stations",
    "lines",
    "direction_end_point",
    "direction_run",
    "undirection_run",
    "plan_run",
    "direction_transfer",
    "undirection_transfer",
    "explore_neighbor",
    "explore_sub_line",
    "direction_stations",
    "direction_lines",
    "source_stations",
    "source_lines",
    "destination_stations",
    "destination_lines",
    "undirection_stations",
    "undirection_lines",
    "undirection_sub_lines",
    "help",
}
```

- [ ] **Step 3: Add baseline scenario groups**

Create explicit `FlowScenario` tuples for:

- mode: up/down/home/end, direction, undirected, plan, rejected quit
- generic lists: movement boundaries and line/station switching
- direction selection: line-first, station-first, endpoint, single-option AUTO
- undirected selection: line, station, sub-line, single-option AUTO
- route planning: source and destination line/station paths
- run modes: forward, reverse, no neighbor, multiple-neighbor exploration
- transfer menus: confirm and return
- help: open, navigate, invoke selected help command, return
- mode/browser returns through `background_state`

Every scenario record must contain a concrete start state, arrangement
function, command, expected final state, success flag, beep flag, navigator
field assertions, and ordered speech substrings.

Use this migration matrix as the minimum scenario inventory:

| Start state | Command/condition | Expected target |
|---|---|---|
| `mode` | direction / undirected / plan selection | `direction_lines` / `undirection_lines` / `source_lines` |
| `mode` | quit with active direction background | `direction_run` |
| `stations` | confirm / line | `lines` |
| `stations` | quit with active background | stored background state |
| `lines` | confirm / station | `stations` |
| `lines` | quit with active background | stored background state |
| `direction_stations` | confirm with line | `direction_end_point` |
| `direction_stations` | confirm without line / line command | `direction_lines` |
| `direction_lines` | confirm with station | `direction_end_point` |
| `direction_lines` | confirm without station / station command | `direction_stations` |
| `direction_lines` | one option on entry | AUTO to `direction_stations` |
| `direction_end_point` | confirm | `direction_run` |
| `undirection_stations` | confirm with line | `undirection_sub_lines` |
| `undirection_stations` | confirm without line / line command | `undirection_lines` |
| `undirection_lines` | confirm with station | `undirection_sub_lines` |
| `undirection_lines` | confirm without station / station command | `undirection_stations` |
| `undirection_lines` | one option on entry | AUTO to `undirection_stations` |
| `undirection_sub_lines` | confirm | `undirection_run` |
| `source_stations` | confirm with line | `destination_lines` |
| `source_stations` | confirm without line / line command | `source_lines` |
| `source_lines` | confirm with station | `destination_lines` |
| `source_lines` | confirm without station / station command | `source_stations` |
| `source_lines` / `source_stations` | one option on entry | AUTO through the corresponding confirm branch |
| `destination_stations` | confirm with line | `plan_run` |
| `destination_stations` | confirm without line / line command | `destination_lines` |
| `destination_lines` | confirm with station | `plan_run` |
| `destination_lines` | confirm without station / station command | `destination_stations` |
| `destination_lines` / `destination_stations` | one option on entry | AUTO through the corresponding confirm branch |
| `direction_run` | left with 0 / 1 / many reverse neighbors | reject / same / `explore_neighbor` |
| `direction_run` | right with 0 / at least 1 forward neighbor | reject / same |
| `direction_run` | transfer with 0 / at least 1 option | reject / `direction_transfer` |
| `direction_run` | endpoint / mode / browser / help | `direction_end_point` / `mode` / `lines` / `help` |
| `undirection_run` | left/right without or with neighbor | reject / same |
| `undirection_run` | transfer with 0 / at least 1 option | reject / `undirection_transfer` |
| `undirection_run` | mode / browser / help | `mode` / `lines` / `help` |
| `plan_run` | left/right without or with neighbor | reject / same |
| `plan_run` | mode / browser / help | `mode` / `lines` / `help` |
| `direction_transfer` | confirm / quit | `direction_run` |
| `undirection_transfer` | confirm / quit | `undirection_run` |
| `explore_neighbor` | confirm / quit | `direction_run` |
| `explore_sub_line` | confirm / quit | `undirection_run` |
| `help` | confirm selected help item | fixed target selected by mutually exclusive return-state/selection guards |
| `help` | quit | fixed stored return state selected by mutually exclusive guards |

For every list-derived state, also cover up/down/home/end at both a successful
movement and a boundary rejection.

- [ ] **Step 4: Add coverage tests for the manifest**

```python
def test_characterization_scenarios_cover_every_legacy_state():
    covered = {scenario.start_state for scenario in FLOW_SCENARIOS}
    assert covered == LEGACY_STATE_IDS


def test_every_legacy_state_has_success_rejection_and_exit_coverage():
    for state_id in LEGACY_STATE_IDS:
        state_scenarios = [
            scenario for scenario in FLOW_SCENARIOS
            if scenario.start_state == state_id
        ]
        assert any(item.expected_success for item in state_scenarios), state_id
        assert any(not item.expected_success for item in state_scenarios), state_id
        assert any(item.expected_state != state_id for item in state_scenarios), state_id
```

- [ ] **Step 5: Run the characterization suite**

Run:

```bash
pytest tests/unit/test_access8graph_flow_characterization.py tests/unit/test_access8graph_flow.py -q
```

Expected: PASS against the legacy flow. If a documented expectation is wrong,
correct the scenario to match observed legacy behavior; do not alter
production.

- [ ] **Step 6: Commit**

```bash
git add tests/unit/access8graph_flow_scenarios.py tests/unit/test_access8graph_flow_characterization.py tests/unit/test_access8graph_flow.py
git commit -m "test: characterize access8graph flow transitions"
```

### Task 8: Milestone 2 Verification

- [ ] **Step 1: Prove production did not change**

Run:

```bash
git diff HEAD~1 -- src
```

Expected: no output.

- [ ] **Step 2: Run all Access8Graph tests**

Run:

```bash
pytest tests/unit/test_access8graph_*.py tests/integration/test_access8graph_mrt_flow.py -q
```

Expected: PASS.

---

## Milestone 3: Parallel Transition Engine

### Task 9: Add Commands, States, Rules, Results, Context, and Effects

**Files:**
- Create: `src/apps/access8graph/navigation/__init__.py`
- Create: `src/apps/access8graph/navigation/model.py`
- Create: `tests/unit/test_access8graph_navigation_model.py`

- [ ] **Step 1: Write enum and rule tests**

```python
from dataclasses import FrozenInstanceError

import pytest

from apps.access8graph.navigation.model import (
    ActionId,
    GuardId,
    NavigationCommand,
    NavigationStateId,
    TransitionOutcome,
    TransitionRule,
)


def test_command_and_state_ids_are_closed_string_enums():
    assert NavigationCommand.DOWN.value == "down"
    assert NavigationCommand.AUTO.value == "auto"
    assert NavigationStateId.MODE.value == "mode"
    assert NavigationStateId.HELP.value == "help"


def test_transition_rule_has_one_fixed_target():
    rule = TransitionRule(
        source=NavigationStateId.MODE,
        command=NavigationCommand.DOWN,
        target=NavigationStateId.MODE,
        action_id=ActionId("move_down"),
        guard_id=GuardId("can_move_down"),
    )

    with pytest.raises(FrozenInstanceError):
        rule.target = NavigationStateId.LINES
    assert not hasattr(rule, "allowed_targets")
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
pytest tests/unit/test_access8graph_navigation_model.py -q
```

Expected: FAIL because the navigation model does not exist.

- [ ] **Step 3: Implement the value objects**

Implement:

- the exact `NavigationCommand` and `NavigationStateId` members from the spec
- `ActionId` and `GuardId` as frozen single-field dataclasses
- `TransitionRule`
- `TransitionOutcome` with `TRANSITIONED`, `HANDLED`, `REJECTED`, `UNHANDLED`
- `PresentationEffects` with ordered close/open/hint/view tuples
- `ActionResult.accepted_with(...)` and `ActionResult.rejected()`
- `TransitionResult`
- `NavigationContext` with state, return state, view, selected mode, and pending
  effects

Do not add target fields to action results.

Use these result signatures consistently in later tasks:

```python
@dataclass(frozen=True, slots=True)
class PresentationEffects:
    close_messages: tuple[object, ...] = ()
    open_messages: tuple[object, ...] = ()
    hints: tuple[object, ...] = ()
    view_items: tuple[object, ...] = ()


@dataclass(frozen=True, slots=True)
class ActionResult:
    accepted: bool
    effects: PresentationEffects = PresentationEffects()

    @classmethod
    def accepted_with(
        cls, effects: PresentationEffects = PresentationEffects()
    ) -> "ActionResult":
        return cls(accepted=True, effects=effects)

    @classmethod
    def rejected(cls) -> "ActionResult":
        return cls(accepted=False)


@dataclass(frozen=True, slots=True)
class TransitionResult:
    outcome: TransitionOutcome
    source: NavigationStateId
    target: NavigationStateId
    effects: PresentationEffects

    @classmethod
    def transitioned(
        cls,
        *,
        source: NavigationStateId,
        target: NavigationStateId,
        effects: PresentationEffects,
    ) -> "TransitionResult":
        return cls(TransitionOutcome.TRANSITIONED, source, target, effects)
```

Add equivalent `handled()` and `rejected()` constructors. Keep
`NavigationContext.current_state` as the canonical mutable state field.

- [ ] **Step 4: Run model tests**

Run:

```bash
pytest tests/unit/test_access8graph_navigation_model.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/apps/access8graph/navigation tests/unit/test_access8graph_navigation_model.py
git commit -m "feat: define access8graph transition model"
```

### Task 10: Add Immutable Snapshots and Pure Guard Contracts

**Files:**
- Create: `src/apps/access8graph/navigation/snapshot.py`
- Create: `tests/unit/test_access8graph_navigation_actions.py`

- [ ] **Step 1: Write snapshot immutability tests**

```python
from dataclasses import FrozenInstanceError

import pytest

from apps.access8graph.navigation.model import NavigationStateId
from apps.access8graph.navigation.snapshot import NavigationSnapshot


def test_navigation_snapshot_is_immutable():
    snapshot = NavigationSnapshot(
        state=NavigationStateId.MODE,
        return_state=None,
        selected_id="direction",
        option_count=3,
        selected_mode=None,
        has_line=False,
        has_station=False,
        has_source=False,
        has_destination=False,
        neighbor_count=0,
        transfer_count=0,
        run_active=False,
    )

    with pytest.raises(FrozenInstanceError):
        snapshot.option_count = 1
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
pytest tests/unit/test_access8graph_navigation_actions.py -q
```

Expected: FAIL because `NavigationSnapshot` does not exist.

- [ ] **Step 3: Implement snapshot and factory**

Create a frozen snapshot with the fields above and a `NavigationSnapshotFactory`
that reads `NavigationContext` plus narrow navigator read ports. The factory
must return plain immutable values, never navigator-owned mutable lists or
dictionaries.

- [ ] **Step 4: Add pure guard type aliases**

In `model.py` define:

```python
Guard = Callable[[NavigationSnapshot], bool]
```

No guard signature receives context, navigator, output, or registry.

- [ ] **Step 5: Run tests**

Run:

```bash
pytest tests/unit/test_access8graph_navigation_actions.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/apps/access8graph/navigation/model.py src/apps/access8graph/navigation/snapshot.py tests/unit/test_access8graph_navigation_actions.py
git commit -m "feat: add immutable navigation snapshots"
```

### Task 11: Implement Transition Table Validation

**Files:**
- Create: `src/apps/access8graph/navigation/table.py`
- Create: `tests/unit/test_access8graph_transition_table.py`

- [ ] **Step 1: Write validator failure tests**

```python
import pytest

from apps.access8graph.navigation.model import (
    ActionId,
    NavigationCommand,
    NavigationStateId,
    TransitionRule,
)
from apps.access8graph.navigation.table import (
    TransitionTableValidationError,
    validate_transition_table,
)


def rule(source, command, target, action="noop", guard=None):
    return TransitionRule(source, command, target, ActionId(action), guard)


def test_validator_rejects_duplicate_unguarded_rules():
    rules = (
        rule(NavigationStateId.MODE, NavigationCommand.DOWN, NavigationStateId.MODE),
        rule(NavigationStateId.MODE, NavigationCommand.DOWN, NavigationStateId.MODE),
    )

    with pytest.raises(TransitionTableValidationError, match="duplicate"):
        validate_transition_table(
            rules=rules,
            initial_state=NavigationStateId.MODE,
            action_ids={ActionId("noop")},
            guard_ids=set(),
        )


def test_validator_rejects_unknown_action():
    rules = (
        rule(NavigationStateId.MODE, NavigationCommand.DOWN, NavigationStateId.MODE),
    )

    with pytest.raises(TransitionTableValidationError, match="action"):
        validate_transition_table(
            rules=rules,
            initial_state=NavigationStateId.MODE,
            action_ids=set(),
            guard_ids=set(),
        )
```

Add separate tests for:

- unguarded plus guarded alternatives
- unknown guard
- invalid initial state
- unreachable state
- missing HELP return
- static AUTO cycle

- [ ] **Step 2: Run and verify failure**

Run:

```bash
pytest tests/unit/test_access8graph_transition_table.py -q
```

Expected: FAIL because the validator does not exist.

- [ ] **Step 3: Implement grouped rule indexing and validation**

Index rules by `(source, command)`. Validate registries, conflicts, graph
reachability from `MODE`, HELP return edges, and unguarded AUTO cycles. Return
an immutable indexed table on success.

- [ ] **Step 4: Run validator tests**

Run:

```bash
pytest tests/unit/test_access8graph_transition_table.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/apps/access8graph/navigation/table.py tests/unit/test_access8graph_transition_table.py
git commit -m "feat: validate access8graph transition tables"
```

### Task 12: Implement Macrosteps, Ambiguity Detection, and AUTO Processing

**Files:**
- Create: `src/apps/access8graph/navigation/engine.py`
- Create: `tests/unit/test_access8graph_transition_engine.py`

- [ ] **Step 1: Write rule-selection and shared-snapshot tests**

```python
def test_all_candidate_guards_receive_the_same_snapshot():
    seen = []

    def first(snapshot):
        seen.append(snapshot)
        return True

    def second(snapshot):
        seen.append(snapshot)
        return False

    engine = build_engine(
        guarded_rules=("first", "second"),
        guards={"first": first, "second": second},
    )

    engine.dispatch(NavigationCommand.CONFIRM)

    assert len(seen) == 2
    assert seen[0] is seen[1]
```

Add tests proving:

- zero matching guards returns `REJECTED`
- two matching guards raise `AmbiguousTransitionError`
- action rejection does not commit target
- action success commits target after action
- action exception does not commit target
- list order does not select a winning guard

- [ ] **Step 2: Run and verify failure**

Run:

```bash
pytest tests/unit/test_access8graph_transition_engine.py -q
```

Expected: FAIL because the engine does not exist.

- [ ] **Step 3: Implement external command dispatch**

Implement exact rule matching, evaluate every guard against one snapshot, call
the selected action, and commit the fixed target only after acceptance.
Propagate unexpected exceptions.

- [ ] **Step 4: Add AUTO tests**

Add tests for:

- a two-step AUTO chain presents one macrostep result
- a new snapshot is built after each accepted transition
- repeated state/rule raises `AutomaticTransitionCycleError`
- 33 automatic steps raise the same error
- an entry handler cannot directly change current state

- [ ] **Step 5: Implement lifecycle and AUTO loop**

Run exit effects, commit target, run entry effects, rebuild snapshot, and
dispatch `AUTO` until stable. Enforce the 32-step limit and visited rule/state
tracking.

- [ ] **Step 6: Run engine tests**

Run:

```bash
pytest tests/unit/test_access8graph_transition_engine.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/apps/access8graph/navigation/engine.py tests/unit/test_access8graph_transition_engine.py
git commit -m "feat: add access8graph transition macrosteps"
```

### Task 13: Implement Lifecycle Presentation

**Files:**
- Create: `src/apps/access8graph/navigation/presenter.py`
- Create: `tests/unit/test_access8graph_flow_presenter.py`

- [ ] **Step 1: Write exact ordering tests**

```python
def test_presenter_orders_effects_and_speaks_once():
    output = RecordingOutput()
    presenter = FlowPresenter(output)
    effects = PresentationEffects(
        close_messages=("old closed",),
        open_messages=("new opened",),
        hints=("hint",),
        view_items=("label", "1 of 2"),
    )

    presenter.present(
        TransitionResult.transitioned(
            source=NavigationStateId.MODE,
            target=NavigationStateId.LINES,
            effects=effects,
        )
    )

    assert output.calls == [
        ("cancel",),
        ("speak", ("old closed", "new opened", "hint", "label", "1 of 2")),
    ]
```

Add tests proving rejected recognized commands beep and speak the current view,
and exceptions before presentation produce no output calls.

- [ ] **Step 2: Run and verify failure**

Run:

```bash
pytest tests/unit/test_access8graph_flow_presenter.py -q
```

Expected: FAIL because `FlowPresenter` does not exist.

- [ ] **Step 3: Implement the presenter**

Flatten non-empty effects in the specified order, cancel once, speak once, and
beep before current-view presentation for `REJECTED`.

- [ ] **Step 4: Run presenter tests**

Run:

```bash
pytest tests/unit/test_access8graph_flow_presenter.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/apps/access8graph/navigation/presenter.py tests/unit/test_access8graph_flow_presenter.py
git commit -m "feat: present access8graph macrostep results"
```

### Task 14: Implement Actions, Lifecycle Handlers, and the Complete Table

**Files:**
- Create: `src/apps/access8graph/navigation/actions.py`
- Complete: `src/apps/access8graph/navigation/table.py`
- Create: `src/apps/access8graph/navigation/flow.py`
- Create: `tests/unit/test_access8graph_transition_parity.py`
- Expand: `tests/unit/test_access8graph_navigation_actions.py`

- [ ] **Step 1: Implement guard registry tests**

For every guarded branch in the characterization matrix, construct its
immutable snapshot and assert exactly one guard returns true:

```python
def test_direction_left_guards_are_mutually_exclusive():
    guards = build_guard_registry()

    for count, expected in (
        (0, "has_no_reverse_neighbor"),
        (1, "has_one_reverse_neighbor"),
        (2, "has_multiple_reverse_neighbors"),
    ):
        snapshot = snapshot_for(
            state=NavigationStateId.DIRECTION_RUN,
            neighbor_count=count,
        )
        matched = {
            guard_id.value
            for guard_id, guard in guards.items()
            if guard_id.value.startswith("has_") and guard(snapshot)
        }
        assert matched == {expected}
```

- [ ] **Step 2: Implement action contract tests**

For each action family, test accepted and rejected paths and assert:

- all failing queries happen before navigator mutation
- no action mutates `context.current_state`
- no action returns a target
- navigator fields and presentation effects match the baseline scenario

- [ ] **Step 3: Implement consolidated registries**

In `actions.py`, implement:

- common list movement and selection
- mode selection/reset
- line/station/source/destination selection
- direction and undirected movement
- route-plan movement
- transfer and neighbor exploration
- help open/invoke/return
- entry view builders and exit/open/hint effects

Use typed `ActionId` and `GuardId` constants. Do not use string-based
`getattr`.

- [ ] **Step 4: Define the complete fixed-target table**

Translate each characterized `if/elif/else` branch into a separate fixed-target
rule. Use `AUTO` rules for every single-option entry path. Ensure every
`NavigationStateId` is reachable and HELP has explicit return rules.

- [ ] **Step 5: Build the new flow adapter**

`TransitionNavigationFlow.enter(command: NavigationCommand) -> TransitionResult`
must dispatch one macrostep and pass the result to `FlowPresenter`. Construction
validates the table before accepting commands.

- [ ] **Step 6: Add parameterized parity tests**

```python
@pytest.mark.parametrize("scenario", FLOW_SCENARIOS, ids=lambda item: item.id)
def test_new_transition_flow_matches_legacy_trace(scenario):
    legacy = run_legacy_scenario(scenario)
    replacement = run_transition_scenario(scenario)

    assert replacement == legacy
```

Normalize only implementation-specific state representation:
`NavigationStateId.MODE` becomes `"mode"` in traces. Do not normalize output
ordering, success/rejection, navigator fields, or beep calls.

- [ ] **Step 7: Run action, table, and parity tests**

Run:

```bash
pytest tests/unit/test_access8graph_navigation_actions.py tests/unit/test_access8graph_transition_table.py tests/unit/test_access8graph_transition_parity.py -q
```

Expected: PASS.

- [ ] **Step 8: Confirm production still uses legacy flow**

Run:

```bash
rg -n "from apps\.access8graph\.flow import MrtFlow" src/apps/access8graph/use_cases/navigation.py
```

Expected: one match in the production factory.

- [ ] **Step 9: Commit**

```bash
git add src/apps/access8graph/navigation tests/unit/test_access8graph_navigation_actions.py tests/unit/test_access8graph_transition_table.py tests/unit/test_access8graph_transition_parity.py
git commit -m "feat: implement access8graph declarative transition flow"
```

### Task 15: Milestone 3 Verification

- [ ] **Step 1: Run all new transition tests**

Run:

```bash
pytest tests/unit/test_access8graph_navigation_model.py tests/unit/test_access8graph_navigation_actions.py tests/unit/test_access8graph_transition_table.py tests/unit/test_access8graph_transition_engine.py tests/unit/test_access8graph_flow_presenter.py tests/unit/test_access8graph_transition_parity.py -q
```

Expected: PASS.

- [ ] **Step 2: Run all Access8Graph tests**

Run:

```bash
pytest tests/unit/test_access8graph_*.py tests/integration/test_access8graph_mrt_flow.py -q
```

Expected: PASS.

---

## Milestone 4: Atomic Cutover and Old Architecture Removal

### Task 16: Switch Translator and Dispatcher to Typed Contracts

**Files:**
- Modify: `src/apps/access8graph/input.py`
- Modify: `src/apps/access8graph/use_cases/command_dispatch.py`
- Modify: `tests/unit/test_access8graph_input.py`
- Modify: `tests/unit/test_access8graph_use_cases.py`

- [ ] **Step 1: Change translator expectations to enum values**

```python
@pytest.mark.parametrize(
    ("usage", "command"),
    [
        (HID.UP, NavigationCommand.UP),
        (HID.DOWN, NavigationCommand.DOWN),
        (HID.ENTER, NavigationCommand.CONFIRM),
        (HID.H, NavigationCommand.OPEN_HELP),
    ],
)
def test_translator_maps_supported_key_down_events(usage, command):
    event = KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=usage,
        pressed=True,
    )

    assert Access8GraphKeyTranslator().translate(event) is command
```

Keep `ESCAPE` outside the translator-to-flow contract because `ModeManager`
intercepts it.

- [ ] **Step 2: Run input tests and verify failure**

Run:

```bash
pytest tests/unit/test_access8graph_input.py -q
```

Expected: FAIL because the translator still returns dictionaries.

- [ ] **Step 3: Return `NavigationCommand` from the translator**

Replace string mappings with enum members and return `NavigationCommand | None`.

- [ ] **Step 4: Add the dispatcher flow protocol**

```python
class NavigationFlow(Protocol):
    def enter(self, command: NavigationCommand) -> TransitionResult: ...
```

The dispatcher continues to:

- consume unknown keys while navigation is active
- return unhandled when no active flow exists
- consume recognized navigation commands after dispatch

- [ ] **Step 5: Run focused tests**

Run:

```bash
pytest tests/unit/test_access8graph_input.py tests/unit/test_access8graph_use_cases.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/apps/access8graph/input.py src/apps/access8graph/use_cases/command_dispatch.py tests/unit/test_access8graph_input.py tests/unit/test_access8graph_use_cases.py
git commit -m "refactor: use typed access8graph navigation commands"
```

### Task 17: Cut Production over to the Transition Flow

**Files:**
- Modify: `src/apps/access8graph/use_cases/navigation.py`
- Modify: `tests/unit/test_access8graph_use_cases.py`
- Modify: `tests/unit/test_access8graph_app_service.py`
- Modify: `tests/integration/test_access8graph_mrt_flow.py`

- [ ] **Step 1: Write factory type and integration expectations**

Update factory tests to assert the created object is
`TransitionNavigationFlow`, then retain the existing graph selection,
start/stop, speech, and error-path assertions.

- [ ] **Step 2: Run and verify failure**

Run:

```bash
pytest tests/unit/test_access8graph_use_cases.py tests/integration/test_access8graph_mrt_flow.py -q
```

Expected: FAIL because `MrtFlowFactory` still constructs legacy `MrtFlow`.

- [ ] **Step 3: Rewire `MrtFlowFactory`**

Construct navigators as before, then assemble:

- `NavigationContext(current_state=NavigationStateId.MODE)`
- snapshot factory
- validated transition table
- guard/action/lifecycle registries
- transition engine
- presenter
- `TransitionNavigationFlow`

Do not change graph/model/navigator construction.

- [ ] **Step 4: Run use-case and integration tests**

Run:

```bash
pytest tests/unit/test_access8graph_use_cases.py tests/unit/test_access8graph_app_service.py tests/integration/test_access8graph_mrt_flow.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/apps/access8graph/use_cases/navigation.py tests/unit/test_access8graph_use_cases.py tests/unit/test_access8graph_app_service.py tests/integration/test_access8graph_mrt_flow.py
git commit -m "refactor: switch access8graph to transition engine"
```

### Task 18: Remove the Legacy Flow

**Files:**
- Delete: `src/apps/access8graph/flow.py`
- Modify: `tests/unit/test_access8graph_flow.py`
- Modify: `tests/unit/test_access8graph_flow_characterization.py`
- Modify: `tests/unit/test_access8graph_transition_parity.py`
- Modify: `tests/unit/access8graph_flow_scenarios.py`
- Modify: `tests/integration/test_access8graph_mrt_flow.py`

- [ ] **Step 1: Remove every surviving legacy flow import**

Update every surviving consumer to import
`apps.access8graph.navigation.flow.TransitionNavigationFlow`, then delete
`src/apps/access8graph/flow.py`. Do not retain `MrtFlow` or an old-module
re-export.

- [ ] **Step 2: Remove the old hierarchy and dictionary tests**

Delete:

- `MrtFlow`
- `State`, `ListState`, `RunState`
- all concrete legacy state classes
- legacy `ListView` and `RunView`
- tests that invoke `flow.enter({"key": ...})`
- temporary parity helpers that instantiate the old flow

Keep the characterization scenarios as tests of the new flow where they remain
valuable.

- [ ] **Step 3: Verify no legacy mechanisms remain**

Run:

```bash
rg -n "class (MrtFlow|State|ListState|RunState)|getattr\\(self\\.state|\"repeat\": 0|\"pressing\": 0|flow\\.enter\\(\\{\"key\"" src tests
```

Expected: no matches.

- [ ] **Step 4: Run Access8Graph regression tests**

Run:

```bash
pytest tests/unit/test_access8graph_*.py tests/integration/test_access8graph_mrt_flow.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/apps/access8graph/flow.py src/apps/access8graph/use_cases/navigation.py tests/unit/test_access8graph_flow.py tests/unit/test_access8graph_flow_characterization.py tests/unit/test_access8graph_transition_parity.py tests/unit/access8graph_flow_scenarios.py tests/integration/test_access8graph_mrt_flow.py
git commit -m "refactor: remove legacy access8graph state flow"
```

### Task 19: Milestone 4 Verification

- [ ] **Step 1: Run the full suite**

Run:

```bash
pytest tests/unit tests/integration -q
```

Expected: PASS.

- [ ] **Step 2: Verify legacy paths and contracts are absent**

Run:

```bash
rg -n "MrtFlow|application\.keyboard|application\.config|application\.state|SpeechServiceProtocol|SpeechSettingsController|allowed_targets|ActionResult.*target_state" src tests
```

Expected: no matches.

---

## Milestone 5: Module Consolidation and Integrity Protection

### Task 20: Split Stable Actions and Tables by Navigation Concern

**Files:**
- Replace: `src/apps/access8graph/navigation/actions.py`
- Replace: `src/apps/access8graph/navigation/table.py`
- Create: `src/apps/access8graph/navigation/actions/__init__.py`
- Create: `src/apps/access8graph/navigation/actions/common.py`
- Create: `src/apps/access8graph/navigation/actions/mode_selection.py`
- Create: `src/apps/access8graph/navigation/actions/direction.py`
- Create: `src/apps/access8graph/navigation/actions/undirected.py`
- Create: `src/apps/access8graph/navigation/actions/route_plan.py`
- Create: `src/apps/access8graph/navigation/actions/transfer.py`
- Create matching modules under `navigation/tables/`
- Create: `src/apps/access8graph/navigation/validation.py`

- [ ] **Step 1: Add assembly equivalence tests**

Before moving code, capture:

```python
def test_family_tables_assemble_the_complete_rule_set():
    rules = build_transition_rules()

    assert {rule.source for rule in rules} == set(NavigationStateId)
    assert len(rules) == len(set(rules))
    validate_transition_table(
        rules=rules,
        initial_state=NavigationStateId.MODE,
        action_ids=set(build_action_registry()),
        guard_ids=set(build_guard_registry()),
    )
```

- [ ] **Step 2: Move actions by concern**

Move code without changing IDs or behavior. Each module exports
`build_actions()`, `build_guards()`, and lifecycle handlers for its concern.
`actions/__init__.py` merges registries and raises on duplicate IDs.

- [ ] **Step 3: Move tables by concern**

Each table module exports `RULES: tuple[TransitionRule, ...]`.
`tables/__init__.py` concatenates groups in a deterministic order; runtime rule
selection remains independent of that order.

- [ ] **Step 4: Move validation into a focused module**

Keep rule declarations in `tables/` and move
`TransitionTableValidator`/exceptions to `validation.py`.

- [ ] **Step 5: Run transition tests**

Run:

```bash
pytest tests/unit/test_access8graph_navigation_actions.py tests/unit/test_access8graph_transition_table.py tests/unit/test_access8graph_transition_engine.py tests/unit/test_access8graph_flow_presenter.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/apps/access8graph/navigation tests/unit/test_access8graph_navigation_actions.py tests/unit/test_access8graph_transition_table.py tests/unit/test_access8graph_transition_engine.py tests/unit/test_access8graph_flow_presenter.py
git commit -m "refactor: group access8graph transitions by concern"
```

### Task 21: Complete Negative Integrity Tests and Extension Documentation

**Files:**
- Modify: `tests/unit/test_access8graph_transition_table.py`
- Modify: `tests/unit/test_access8graph_transition_engine.py`
- Create: `docs/access8graph-transition-engine.md`

- [ ] **Step 1: Add the complete negative matrix**

Parameterize validator failures for:

```python
VALIDATION_CASES = (
    ("duplicate rule", duplicate_rules(), "duplicate"),
    ("unguarded conflict", mixed_guard_rules(), "unguarded"),
    ("unknown action", unknown_action_rules(), "action"),
    ("unknown guard", unknown_guard_rules(), "guard"),
    ("unreachable state", unreachable_rules(), "unreachable"),
    ("invalid initial state", valid_rules(), "initial"),
    ("missing help return", no_help_return_rules(), "HELP"),
    ("auto cycle", auto_cycle_rules(), "AUTO"),
)
```

Add runtime tests for two successful guards and 33 AUTO transitions.

- [ ] **Step 2: Write extension documentation**

Document this exact process:

1. Add a `NavigationCommand` or `NavigationStateId` enum member.
2. Add snapshot facts only when a pure guard requires them.
3. Register a pure guard for each mutually exclusive data branch.
4. Register an action that validates before mutation and never selects target.
5. Add fixed-target rules in the appropriate family table.
6. Add lifecycle presentation without state mutation.
7. Add characterization/contract cases.
8. Run validator, transition, Access8Graph, and full suites.

Include one fixed-target guarded example and one `AUTO` example.

- [ ] **Step 3: Run integrity tests**

Run:

```bash
pytest tests/unit/test_access8graph_transition_table.py tests/unit/test_access8graph_transition_engine.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/unit/test_access8graph_transition_table.py tests/unit/test_access8graph_transition_engine.py docs/access8graph-transition-engine.md
git commit -m "docs: define access8graph transition extension contract"
```

### Task 22: Final Verification

- [ ] **Step 1: Run targeted architecture tests**

Run:

```bash
pytest tests/unit/test_json_speech_settings_store.py tests/unit/test_output_ports.py tests/unit/test_speech_runtime_settings.py tests/unit/test_panel_controller.py tests/unit/test_tool_app_shell.py tests/unit/test_tray_icon.py tests/unit/test_nvda_remote_use_cases.py tests/unit/test_access8graph_navigation_model.py tests/unit/test_access8graph_navigation_actions.py tests/unit/test_access8graph_transition_table.py tests/unit/test_access8graph_transition_engine.py tests/unit/test_access8graph_flow_presenter.py -q
```

Expected: PASS.

- [ ] **Step 2: Run all Access8Graph tests**

Run:

```bash
pytest tests/unit/test_access8graph_*.py tests/integration/test_access8graph_mrt_flow.py -q
```

Expected: PASS.

- [ ] **Step 3: Run the complete suite**

Run:

```bash
pytest tests/unit tests/integration -q
```

Expected: PASS.

- [ ] **Step 4: Run final architecture scans**

Run:

```bash
rg -n "application\.keyboard|application\.config|application\.state|SpeechServiceProtocol|SpeechSettingsController|apps\.shared\.(panel_controller|tool_app_shell|tray_icon)|getattr\\(self\\.state|allowed_targets|ActionResult.*target_state" src tests
```

Expected: no matches.

- [ ] **Step 5: Inspect final diff and history**

Run:

```bash
git status --short
git log --oneline --decorate -20
```

Expected: no uncommitted implementation changes; each task is represented by a
focused commit.
