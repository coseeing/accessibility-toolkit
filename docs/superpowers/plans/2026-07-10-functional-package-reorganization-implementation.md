# Accessibility Toolkit Functional Package Reorganization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the technical-layer-oriented `accessibility_toolkit` package tree with a single function-oriented structure organized around input, output, scheduling, interaction, events, remote, and runtime.

**Architecture:** Perform a hard-cut package migration with no compatibility modules or deprecated re-exports. Move one functional domain at a time, update every repository consumer in the same task, and keep behavior stable. Current dependency direction is `output -> scheduling`, `interaction -> input/events`, `remote -> output.speech`, and `runtime -> all functional domains`; `input -> scheduling` is only a permitted future edge. No functional domain may depend on runtime, and no domain other than runtime or applications may depend on remote.

**Tech Stack:** Python 3.11+, setuptools, pytest, wxPython, PyInstaller, existing Windows/macOS platform integrations

**Specifications:**

- `docs/superpowers/specs/2026-07-10-functional-package-reorganization-design.md`
- `docs/superpowers/specs/2026-07-10-functional-package-reorganization-design_zh-TW.md`

---

## Global Constraints

- Do not create modules under the old `application`, `application_support`, `interop`, or `adapters` paths that forward imports to the new structure.
- Do not leave deprecated re-exports in old package `__init__.py` files.
- Preserve behavior, callback signatures, protocol payloads, configuration schema, and persisted engine IDs.
- Keep `remote` in `accessibility-toolkit-core`, while preventing input, output, scheduling, interaction, and events from importing it.
- Keep the scheduler domain-neutral even though output is its first current consumer.
- Do not add input scheduling behavior; `input -> scheduling` is permitted only as a future dependency and is absent in this refactor.
- Every first-level feature package and the public `output.speech`, `input.windows`, `input.macos`, `remote.routing`, `remote.session`, and `remote.transport` packages define explicit `__all__` lists.
- No feature package imports `runtime`; the NVDA Controller driver resolves `vendor/nvda/x64/nvdaControllerClient.dll` relative to its own `__file__`.
- Core package discovery is exactly `include = ["accessibility_toolkit", "accessibility_toolkit.*"]`.
- Python support remains `>=3.11`; do not add runtime dependencies.
- Preserve all user-owned unrelated working-tree changes.
- Run focused tests after each domain move and the full suite after all old namespaces are deleted.

## Target File Structure

| Target | Responsibility |
|---|---|
| `src/accessibility_toolkit/input/` | HID/key models, capture contracts, activation, keyboard pipeline, policies, and platform input implementations |
| `src/accessibility_toolkit/output/` | Output contracts, queueing, capabilities, clipboard, tone, wave, braille, and platform output implementations |
| `src/accessibility_toolkit/output/speech/` | Speech commands, sequences, service, backends, settings, persistence, facades, and drivers |
| `src/accessibility_toolkit/scheduling/` | Domain-neutral scheduling, cancellation, completion, and timeout primitives |
| `src/accessibility_toolkit/interaction/` | Mode protocol and mode lifecycle coordination |
| `src/accessibility_toolkit/events/` | Cross-functional application lifecycle event dataclasses |
| `src/accessibility_toolkit/remote/` | Relay messages, serialization, routing, session, and transport |
| `src/accessibility_toolkit/runtime/` | Environment, platform selection, and application composition |

## Import Migration Manifest

Apply these exact module ownership changes throughout `src/`, `tests/`, current documentation, monkeypatch strings, and fake `sys.modules` keys. Historical Superpowers documents are excluded.

| Old module | New module |
|---|---|
| `accessibility_toolkit.application.events` | `accessibility_toolkit.events` or `accessibility_toolkit.events.application` |
| `accessibility_toolkit.application.output.scheduler` | `accessibility_toolkit.scheduling` or `accessibility_toolkit.scheduling.scheduler` |
| `accessibility_toolkit.interop.key.hid` | `accessibility_toolkit.input.hid` |
| `accessibility_toolkit.interop.key.key_event` | `accessibility_toolkit.input.events` |
| `accessibility_toolkit.interop.key` | `accessibility_toolkit.input` |
| `accessibility_toolkit.adapters.inputs.base` | `accessibility_toolkit.input.capture` |
| `accessibility_toolkit.adapters.inputs.captured_event` | `accessibility_toolkit.input.events` |
| `accessibility_toolkit.application.input.activation` | `accessibility_toolkit.input.activation` |
| `accessibility_toolkit.application.input.keyboard_pipeline` | `accessibility_toolkit.input.pipeline` |
| `accessibility_toolkit.application.input.results` | `accessibility_toolkit.input.results` |
| `accessibility_toolkit.application.input.service` | `accessibility_toolkit.input.service` |
| `accessibility_toolkit.application.input.active_key_policy` | `accessibility_toolkit.input.policies` |
| `accessibility_toolkit.application.input.system_toggle_policy` | `accessibility_toolkit.input.policies` |
| `accessibility_toolkit.adapters.windows.{hid_map,hotkey,keyboard_hook,native_key_context}` | `accessibility_toolkit.input.windows.{hid_map,hotkey,keyboard_hook,native_key_context}` |
| `accessibility_toolkit.adapters.macos.*` | `accessibility_toolkit.input.macos.*` |
| `accessibility_toolkit.application.output.{capabilities,clipboard,ports}` | `accessibility_toolkit.output.{capabilities,clipboard,ports}` |
| `accessibility_toolkit.application.output.service` | `accessibility_toolkit.output.queue` |
| `accessibility_toolkit.adapters.outputs.interfaces` | `accessibility_toolkit.output.interfaces` |
| `accessibility_toolkit.adapters.outputs.{tone,wave,braille}` | `accessibility_toolkit.output.{tone,wave,braille}` |
| `accessibility_toolkit.adapters.outputs.speech` | `accessibility_toolkit.output.speech.null` |
| `accessibility_toolkit.interop.speech.speech_commands` | `accessibility_toolkit.output.speech.commands` |
| `accessibility_toolkit.interop.speech.speech_sequence` | `accessibility_toolkit.output.speech.sequence` |
| `accessibility_toolkit.application.output.speech.*` | `accessibility_toolkit.output.speech.*` |
| `accessibility_toolkit.application_support.speech_runtime_settings` | `accessibility_toolkit.output.speech.runtime_settings` |
| `accessibility_toolkit.application_support.speech_settings_facade` | `accessibility_toolkit.output.speech.settings_facade` |
| `accessibility_toolkit.adapters.config.json_speech_settings` | `accessibility_toolkit.output.speech.json_settings_store` |
| `accessibility_toolkit.adapters.outputs.drivers.pyttsx3` | `accessibility_toolkit.output.speech.drivers.pyttsx3` |
| `accessibility_toolkit.adapters.windows.nvda_controller` | `accessibility_toolkit.output.speech.windows.nvda_controller` |
| `accessibility_toolkit.adapters.windows.clipboard` | `accessibility_toolkit.output.windows.clipboard` |
| `accessibility_toolkit.application_support.{mode_manager,mode_types}` | `accessibility_toolkit.interaction.modes` |
| `accessibility_toolkit.interop.protocol` | `accessibility_toolkit.remote` |
| `accessibility_toolkit.interop.protocol.routing` | `accessibility_toolkit.remote.routing` |
| `accessibility_toolkit.interop.protocol.session` | `accessibility_toolkit.remote.session` |
| `accessibility_toolkit.interop.protocol.transport` | `accessibility_toolkit.remote.transport` |

### Task 1: Establish the Scheduling and Event Foundations

**Files:**

- Move: `src/accessibility_toolkit/application/output/scheduler.py` -> `src/accessibility_toolkit/scheduling/scheduler.py`
- Create: `src/accessibility_toolkit/scheduling/__init__.py`
- Move: `src/accessibility_toolkit/application/events.py` -> `src/accessibility_toolkit/events/application.py`
- Create: `src/accessibility_toolkit/events/__init__.py`
- Modify: `src/accessibility_toolkit/application/output/__init__.py`
- Modify: all source and test consumers of scheduler or application events
- Rename: `tests/unit/test_output_scheduler.py` -> `tests/unit/test_scheduling.py`
- Rename: `tests/unit/test_application_events.py` -> `tests/unit/test_toolkit_events.py`

**Interfaces:**

- Consumes: only Python standard-library types.
- Produces: `Scheduler`, `CancellationToken`, `ScheduledFuture`, `EventCallbacks` from `accessibility_toolkit.scheduling`; `AppEvent` and six lifecycle dataclasses from `accessibility_toolkit.events`.

- [ ] **Step 1: Change the focused tests to require the new public imports**

```bash
git mv tests/unit/test_output_scheduler.py tests/unit/test_scheduling.py
git mv tests/unit/test_application_events.py tests/unit/test_toolkit_events.py
```

Update the scheduler tests to import:

```python
from accessibility_toolkit.scheduling import (
    CancellationToken,
    EventCallbacks,
    ScheduledFuture,
    Scheduler,
)
```

Update the toolkit event tests to import lifecycle event classes from:

```python
from accessibility_toolkit.events import AppEvent, ErrorRaised, ModeChanged
```

- [ ] **Step 2: Run the focused tests and verify the new packages are missing**

Run:

```bash
pytest tests/unit/test_scheduling.py tests/unit/test_toolkit_events.py -v
```

Expected: FAIL with `ModuleNotFoundError` for `accessibility_toolkit.scheduling` or `accessibility_toolkit.events`.

- [ ] **Step 3: Move the implementations and define explicit public APIs**

Perform the pure moves first:

```bash
mkdir -p src/accessibility_toolkit/scheduling src/accessibility_toolkit/events
git mv src/accessibility_toolkit/application/output/scheduler.py src/accessibility_toolkit/scheduling/scheduler.py
git mv src/accessibility_toolkit/application/events.py src/accessibility_toolkit/events/application.py
```

`accessibility_toolkit.scheduling.__all__` must export only:

```python
[
    "CancellationToken",
    "EventCallbacks",
    "ScheduledFuture",
    "Scheduler",
]
```

`accessibility_toolkit.events.__all__` must export the six lifecycle event dataclasses plus `AppEvent`.

- [ ] **Step 4: Update every scheduler and event consumer**

Update imports in:

- `src/accessibility_toolkit/runtime/output.py`
- `src/accessibility_toolkit/runtime/platform.py`
- output services and speech backends that use `Scheduler`
- Windows NVDA Controller and pyttsx3 implementations
- all three app entrypoints and services
- all UI and unit/integration tests that consume toolkit events

Remove scheduler exports from the old `application.output.__init__`; do not forward event imports from `application.events`.

- [ ] **Step 5: Run focused and dependent tests**

Run:

```bash
pytest tests/unit/test_scheduling.py tests/unit/test_toolkit_events.py tests/unit/test_output_service.py tests/unit/test_bootstrap_output.py tests/unit/test_app_events.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit the foundation move**

```bash
git add src/accessibility_toolkit src/apps src/ui tests
git commit -m "refactor: move scheduling and events by function"
```

### Task 2: Consolidate the Input Domain

**Files:**

- Create: `src/accessibility_toolkit/input/__init__.py`
- Move: `src/accessibility_toolkit/interop/key/hid.py` -> `src/accessibility_toolkit/input/hid.py`
- Move/merge: `src/accessibility_toolkit/interop/key/key_event.py` and `src/accessibility_toolkit/adapters/inputs/captured_event.py` -> `src/accessibility_toolkit/input/events.py`
- Move: `src/accessibility_toolkit/adapters/inputs/base.py` -> `src/accessibility_toolkit/input/capture.py`
- Move: `src/accessibility_toolkit/application/input/activation.py` -> `src/accessibility_toolkit/input/activation.py`
- Move: `src/accessibility_toolkit/application/input/keyboard_pipeline.py` -> `src/accessibility_toolkit/input/pipeline.py`
- Move: `src/accessibility_toolkit/application/input/results.py` -> `src/accessibility_toolkit/input/results.py`
- Move: `src/accessibility_toolkit/application/input/service.py` -> `src/accessibility_toolkit/input/service.py`
- Merge: `src/accessibility_toolkit/application/input/{active_key_policy,system_toggle_policy}.py` -> `src/accessibility_toolkit/input/policies.py`
- Move: Windows keyboard/hotkey/HID/native-context files -> `src/accessibility_toolkit/input/windows/`
- Move: macOS event-tap/keyboard/hotkey/HID/keymap/permissions files -> `src/accessibility_toolkit/input/macos/`
- Modify: `src/accessibility_toolkit/runtime/platform.py`
- Modify: `src/accessibility_toolkit/runtime/runtime_parts.py`
- Modify: all app, UI, and test input imports
- Rename: `tests/unit/test_macos_adapters.py` -> `tests/unit/test_macos_input.py`

**Interfaces:**

- Consumes: `AppEvent` types only through application callbacks; no scheduling dependency is introduced.
- Produces: `HID`, `KeyEvent`, `CapturedKeyEvent`, `InputCapture`, `HotkeyCapture`, `KeyEventDecision`, `InputActivationUseCase`, `AppKeyEventResult`, `KeyboardPipelineResult`, `KeyboardInputService`, `KeyEventHandler`, `ActiveKeyEventPolicy`, and `should_pass_through_system_toggle`; platform APIs live under `input.windows` and `input.macos`.

- [ ] **Step 1: Update focused tests to the target input imports**

```bash
git mv tests/unit/test_macos_adapters.py tests/unit/test_macos_input.py
```

Use the public entrypoint for shared concepts:

```python
from accessibility_toolkit.input import (
    AppKeyEventResult,
    CapturedKeyEvent,
    HID,
    InputActivationUseCase,
    KeyEvent,
    KeyboardInputService,
)
```

Use `accessibility_toolkit.input.windows` and `accessibility_toolkit.input.macos` for platform implementations. Update string-based monkeypatch targets and fake `sys.modules` keys, not only normal imports.

- [ ] **Step 2: Run focused tests and verify failure at the new boundary**

Run:

```bash
pytest tests/unit/test_hid_keys.py tests/unit/test_keyboard_input_service.py tests/unit/test_input_activation.py tests/unit/test_input_policies.py tests/unit/test_macos_input.py tests/unit/test_windows_adapters.py -v
```

Expected: FAIL because `accessibility_toolkit.input` does not yet exist.

- [ ] **Step 3: Move input models, contracts, pipeline, and policies**

Use this move manifest:

```bash
mkdir -p src/accessibility_toolkit/input/windows src/accessibility_toolkit/input/macos
git mv src/accessibility_toolkit/interop/key/hid.py src/accessibility_toolkit/input/hid.py
git mv src/accessibility_toolkit/interop/key/key_event.py src/accessibility_toolkit/input/events.py
git mv src/accessibility_toolkit/adapters/inputs/base.py src/accessibility_toolkit/input/capture.py
git mv src/accessibility_toolkit/application/input/activation.py src/accessibility_toolkit/input/activation.py
git mv src/accessibility_toolkit/application/input/keyboard_pipeline.py src/accessibility_toolkit/input/pipeline.py
git mv src/accessibility_toolkit/application/input/results.py src/accessibility_toolkit/input/results.py
git mv src/accessibility_toolkit/application/input/service.py src/accessibility_toolkit/input/service.py
git mv src/accessibility_toolkit/application/input/active_key_policy.py src/accessibility_toolkit/input/policies.py
```

Append `CapturedKeyEvent` to `input/events.py`, append `should_pass_through_system_toggle` to `input/policies.py`, and delete the two absorbed source files. Keep the Windows type import local so importing `accessibility_toolkit.input` does not initialize `input.windows`:

```python
@dataclass(frozen=True)
class CapturedKeyEvent:
    key_event: KeyEvent
    native_context: object | None = None
    num_lock_on: bool | None = None


def should_pass_through_system_toggle(event: CapturedKeyEvent) -> bool:
    from accessibility_toolkit.input.windows.native_key_context import WindowsNativeKeyContext

    return (
        event.key_event.usage == HID.NUM_LOCK
        and isinstance(event.native_context, WindowsNativeKeyContext)
    )
```

Preserve the existing type shapes and enum values. When merging event and policy files, change imports only; do not change decision behavior.

Define a deliberate `input.__all__` containing the shared models, contracts, pipeline results, service, activation use case, and policies. Do not re-export platform implementations from the cross-platform `input` root.

- [ ] **Step 4: Move Windows and macOS input implementations**

```bash
git mv src/accessibility_toolkit/adapters/windows/hid_map.py src/accessibility_toolkit/input/windows/hid_map.py
git mv src/accessibility_toolkit/adapters/windows/hotkey.py src/accessibility_toolkit/input/windows/hotkey.py
git mv src/accessibility_toolkit/adapters/windows/keyboard_hook.py src/accessibility_toolkit/input/windows/keyboard_hook.py
git mv src/accessibility_toolkit/adapters/windows/native_key_context.py src/accessibility_toolkit/input/windows/native_key_context.py
git mv src/accessibility_toolkit/adapters/macos/event_tap.py src/accessibility_toolkit/input/macos/event_tap.py
git mv src/accessibility_toolkit/adapters/macos/hid_map.py src/accessibility_toolkit/input/macos/hid_map.py
git mv src/accessibility_toolkit/adapters/macos/hotkey.py src/accessibility_toolkit/input/macos/hotkey.py
git mv src/accessibility_toolkit/adapters/macos/keyboard_hook.py src/accessibility_toolkit/input/macos/keyboard_hook.py
git mv src/accessibility_toolkit/adapters/macos/keymap.py src/accessibility_toolkit/input/macos/keymap.py
git mv src/accessibility_toolkit/adapters/macos/permissions.py src/accessibility_toolkit/input/macos/permissions.py
```

Create platform `__init__.py` files with explicit `__all__` declarations. Keep lazy platform imports in runtime so importing `accessibility_toolkit.input` on Linux does not eagerly load Win32 or PyObjC APIs.

- [ ] **Step 5: Update all input consumers and runtime platform loading**

Update:

- `src/apps/access8graph/*`, `src/apps/key_echo/*`, and `src/apps/nvda_remote/*`
- `src/accessibility_toolkit/interaction` consumers created later by the mode move
- `src/accessibility_toolkit/runtime/platform.py` and `runtime_parts.py`
- tests, including monkeypatch strings and fake module names

Remove `_import_compat_module()` fallback behavior for old `adapters.macos` paths. Runtime must load only the new functional paths.

- [ ] **Step 6: Run input and application regression tests**

Run:

```bash
pytest tests/unit/test_hid_keys.py tests/unit/test_keyboard_input_service.py tests/unit/test_input_activation.py tests/unit/test_input_policies.py tests/unit/test_macos_input.py tests/unit/test_windows_adapters.py tests/unit/test_key_echo_app_service.py tests/unit/test_access8graph_app_service.py tests/unit/test_nvda_remote_app_service.py -v
```

Expected: PASS.

- [ ] **Step 7: Verify removed input-layer imports are gone**

Run:

```bash
rg -n "accessibility_toolkit\.(interop\.key|adapters\.(inputs|windows\.(keyboard_hook|hotkey|hid_map|native_key_context)|macos)|application\.input)" src tests
```

Expected: no matches.

- [ ] **Step 8: Commit the input domain move**

```bash
git add src tests
git commit -m "refactor: consolidate toolkit input package"
```

### Task 3: Consolidate Output and Speech

**Files:**

- Create: `src/accessibility_toolkit/output/__init__.py`
- Move: `src/accessibility_toolkit/application/output/{capabilities,clipboard,ports}.py` -> `src/accessibility_toolkit/output/`
- Move: `src/accessibility_toolkit/application/output/service.py` -> `src/accessibility_toolkit/output/queue.py`
- Move: `src/accessibility_toolkit/adapters/outputs/interfaces.py` -> `src/accessibility_toolkit/output/interfaces.py`
- Move: tone/wave/braille implementations -> `src/accessibility_toolkit/output/`
- Move: speech service/backend/settings/store modules -> `src/accessibility_toolkit/output/speech/`
- Move: speech command/sequence models -> `src/accessibility_toolkit/output/speech/`
- Move: `JsonSpeechSettingsStore` -> `src/accessibility_toolkit/output/speech/json_settings_store.py`
- Move: speech runtime settings coordinator and facade -> `src/accessibility_toolkit/output/speech/`
- Move: pyttsx3 driver -> `src/accessibility_toolkit/output/speech/drivers/pyttsx3.py`
- Move: NVDA Controller and DLL -> `src/accessibility_toolkit/output/speech/windows/`
- Move: Windows clipboard -> `src/accessibility_toolkit/output/windows/clipboard.py`
- Modify: `src/accessibility_toolkit/runtime/output.py`
- Modify: `src/accessibility_toolkit/runtime/platform.py`
- Modify: `src/accessibility_toolkit/runtime/runtime_parts.py`
- Modify: all app, remote, UI, and test output imports

**Interfaces:**

- Consumes: `Scheduler` from `accessibility_toolkit.scheduling`.
- Produces: output protocols and `QueuedService` from `accessibility_toolkit.output`; speech commands, `SpeechSequence`, speech services/settings, and backend management from `accessibility_toolkit.output.speech`; implementation APIs from explicit driver/platform submodules.

- [ ] **Step 1: Update output and speech tests to require the target imports**

Use these public roots where applicable:

```python
from accessibility_toolkit.output import Capabilities, QueuedService
from accessibility_toolkit.output.speech import (
    SpeechEngineOption,
    SpeechSequence,
    SpeechService,
)
```

Use specific submodules for drivers, platform implementations, and implementation details. Update monkeypatch target strings.

- [ ] **Step 2: Run focused output tests and verify failure**

Run:

```bash
pytest tests/unit/test_output_ports.py tests/unit/test_output_service.py tests/unit/test_speech_service.py tests/unit/test_speech_backends.py tests/unit/test_speech_commands.py tests/unit/test_speech_runtime_settings.py tests/unit/test_speech_settings_facade.py tests/unit/test_json_speech_settings_store.py tests/unit/test_tone_output.py tests/unit/test_clipboard_service.py -v
```

Expected: FAIL because the target output packages are incomplete or missing.

- [ ] **Step 3: Move generic output contracts and implementations**

```bash
mkdir -p src/accessibility_toolkit/output/windows src/accessibility_toolkit/output/speech/drivers src/accessibility_toolkit/output/speech/windows/vendor/nvda/x64
git mv src/accessibility_toolkit/application/output/capabilities.py src/accessibility_toolkit/output/capabilities.py
git mv src/accessibility_toolkit/application/output/clipboard.py src/accessibility_toolkit/output/clipboard.py
git mv src/accessibility_toolkit/application/output/ports.py src/accessibility_toolkit/output/ports.py
git mv src/accessibility_toolkit/application/output/service.py src/accessibility_toolkit/output/queue.py
git mv src/accessibility_toolkit/adapters/outputs/interfaces.py src/accessibility_toolkit/output/interfaces.py
git mv src/accessibility_toolkit/adapters/outputs/tone.py src/accessibility_toolkit/output/tone.py
git mv src/accessibility_toolkit/adapters/outputs/wave.py src/accessibility_toolkit/output/wave.py
git mv src/accessibility_toolkit/adapters/outputs/braille.py src/accessibility_toolkit/output/braille.py
git mv src/accessibility_toolkit/adapters/outputs/speech.py src/accessibility_toolkit/output/speech/null.py
git mv src/accessibility_toolkit/adapters/windows/clipboard.py src/accessibility_toolkit/output/windows/clipboard.py
git rm 'src/accessibility_toolkit/adapters/outputs/ref𦳒.txt'
```

Keep `ClipboardService` as the cross-platform protocol in `output.clipboard`; put `WindowsClipboardService` in `output.windows.clipboard`. Keep output protocols independent of platform modules.

Rename only the module containing `QueuedService` from `service.py` to `queue.py`; preserve the class name and `Mode` enum values.

- [ ] **Step 4: Move all speech-owned models and behavior together**

```bash
git mv src/accessibility_toolkit/interop/speech/speech_commands.py src/accessibility_toolkit/output/speech/commands.py
git mv src/accessibility_toolkit/interop/speech/speech_sequence.py src/accessibility_toolkit/output/speech/sequence.py
git mv src/accessibility_toolkit/application/output/speech/backends.py src/accessibility_toolkit/output/speech/backends.py
git mv src/accessibility_toolkit/application/output/speech/service.py src/accessibility_toolkit/output/speech/service.py
git mv src/accessibility_toolkit/application/output/speech/settings.py src/accessibility_toolkit/output/speech/settings.py
git mv src/accessibility_toolkit/application/output/speech/settings_store.py src/accessibility_toolkit/output/speech/settings_store.py
git mv src/accessibility_toolkit/adapters/config/json_speech_settings.py src/accessibility_toolkit/output/speech/json_settings_store.py
git mv src/accessibility_toolkit/application_support/speech_runtime_settings.py src/accessibility_toolkit/output/speech/runtime_settings.py
git mv src/accessibility_toolkit/application_support/speech_settings_facade.py src/accessibility_toolkit/output/speech/settings_facade.py
git mv src/accessibility_toolkit/adapters/outputs/drivers/pyttsx3.py src/accessibility_toolkit/output/speech/drivers/pyttsx3.py
git mv src/accessibility_toolkit/adapters/windows/nvda_controller.py src/accessibility_toolkit/output/speech/windows/nvda_controller.py
git mv src/accessibility_toolkit/adapters/windows/vendor/nvda/x64/nvdaControllerClient.dll src/accessibility_toolkit/output/speech/windows/vendor/nvda/x64/nvdaControllerClient.dll
```

Move commands, sequences, service, backend management, numeric settings, store protocol, JSON store, runtime settings coordinator, and settings facade under `output.speech`.

The output/speech public API must export common models and services, while JSON persistence, drivers, and platform implementations remain available through explicit submodule paths.

- [ ] **Step 5: Move output drivers and the vendored NVDA DLL**

Use these target implementation paths:

```text
accessibility_toolkit.output.speech.drivers.pyttsx3
accessibility_toolkit.output.speech.windows.nvda_controller
accessibility_toolkit.output.windows.clipboard
```

Place the DLL at:

```text
src/accessibility_toolkit/output/speech/windows/vendor/nvda/x64/nvdaControllerClient.dll
```

Keep runtime loading lazy so unsupported platforms can import the cross-platform packages.

Replace the driver’s runtime resource dependency with package-relative ownership:

```python
from pathlib import Path

VENDORED_X64_DLL = (
    Path(__file__).resolve().parent
    / "vendor"
    / "nvda"
    / "x64"
    / "nvdaControllerClient.dll"
)

# In load_default():
candidate = str(VENDORED_X64_DLL)
```

Update the two NVDA Controller load tests in `tests/unit/test_windows_adapters.py` to monkeypatch `VENDORED_X64_DLL` directly to `vendored_path`; remove monkeypatches of `resource_path`. Assert that `accessibility_toolkit.output.speech.windows.nvda_controller` does not load `accessibility_toolkit.runtime` during an isolated import.

- [ ] **Step 6: Update output consumers, including remote wire models**

Update all apps and runtime builders. Update `remote.serializer` and `remote.routing` consumers to import speech commands and sequences from `output.speech`; this is the intentional `remote -> output.speech` dependency.

- [ ] **Step 7: Run focused output, runtime, and integration tests**

Run:

```bash
pytest tests/unit/test_output_ports.py tests/unit/test_output_service.py tests/unit/test_speech_service.py tests/unit/test_speech_backends.py tests/unit/test_speech_commands.py tests/unit/test_speech_runtime_settings.py tests/unit/test_speech_settings_facade.py tests/unit/test_json_speech_settings_store.py tests/unit/test_tone_output.py tests/unit/test_clipboard_service.py tests/unit/test_bootstrap_output.py tests/unit/test_bootstrap_platform.py tests/integration/test_speech_engine_persistence_and_routing.py -v
```

Expected: PASS.

- [ ] **Step 8: Verify old output imports are gone**

Run:

```bash
rg -n "accessibility_toolkit\.(application\.output|application_support\.speech|interop\.speech|adapters\.(config|outputs|windows\.(clipboard|nvda_controller)))" src tests
```

Expected: no matches.

- [ ] **Step 9: Commit the output domain move**

```bash
git add src tests
git commit -m "refactor: consolidate toolkit output package"
```

### Task 4: Move Interaction Modes

**Files:**

- Move/merge: `src/accessibility_toolkit/application_support/{mode_manager,mode_types}.py` -> `src/accessibility_toolkit/interaction/modes.py`
- Create: `src/accessibility_toolkit/interaction/__init__.py`
- Modify: all app and test mode imports

**Interfaces:**

- Consumes: `KeyEvent` and `AppKeyEventResult` from `accessibility_toolkit.input`, plus `ModeChanged` from `accessibility_toolkit.events`.
- Produces: `ActivationMode` and `ModeManager` from `accessibility_toolkit.interaction`.

- [ ] **Step 1: Update mode tests to the target import**

```python
from accessibility_toolkit.interaction import ActivationMode, ModeManager
```

- [ ] **Step 2: Run the mode tests and verify failure**

Run:

```bash
pytest tests/unit/test_mode_manager.py -v
```

Expected: FAIL because `accessibility_toolkit.interaction` is missing.

- [ ] **Step 3: Move mode coordination into interaction**

```bash
mkdir -p src/accessibility_toolkit/interaction
git mv src/accessibility_toolkit/application_support/mode_manager.py src/accessibility_toolkit/interaction/modes.py
```

Move the `ActivationMode` protocol from `application_support/mode_types.py` into `interaction/modes.py`, update its imports to the Task 2 public API, and delete `mode_types.py`. `interaction/__init__.py` contains:

```python
from accessibility_toolkit.interaction.modes import ActivationMode, ModeManager

__all__ = ["ActivationMode", "ModeManager"]
```

Preserve mode entry, exit, capture rollback, exit-key behavior, and `ModeChanged` notification semantics. Import input models from `accessibility_toolkit.input` and lifecycle events from `accessibility_toolkit.events`.

- [ ] **Step 4: Update all app mode consumers**

Update the three app services and their tests. Do not move app-specific modes or navigation rules into the toolkit.

- [ ] **Step 5: Run interaction and app regression tests**

Run:

```bash
pytest tests/unit/test_mode_manager.py tests/unit/test_key_echo_app_service.py tests/unit/test_access8graph_app_service.py tests/unit/test_nvda_remote_app_service.py tests/unit/test_key_echo_use_cases.py tests/unit/test_nvda_remote_use_cases.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit the interaction move**

```bash
git add src tests
git commit -m "refactor: move mode lifecycle into interaction"
```

### Task 5: Consolidate the Remote Domain

**Files:**

- Move: `src/accessibility_toolkit/interop/protocol/connection_info.py` -> `src/accessibility_toolkit/remote/connection.py`
- Move: protocol messages, serializer, and events -> `src/accessibility_toolkit/remote/`
- Move: routing, session, and transport trees -> `src/accessibility_toolkit/remote/`
- Create/modify: all `remote` package `__init__.py` files
- Modify: NVDA Remote app, protocol tests, and integration tests

**Interfaces:**

- Consumes: `SpeechSequence` and restore helpers from `accessibility_toolkit.output.speech` to preserve the relay wire format.
- Produces: connection/message/serializer/event API from `accessibility_toolkit.remote`, `MessageRouter` from `remote.routing`, `RemoteSession` from `remote.session`, and `Transport`/`RelayTransport` from `remote.transport`.

- [ ] **Step 1: Update protocol tests to require the remote API**

Use:

```python
from accessibility_toolkit.remote import (
    ConnectionInfo,
    ConnectionMode,
    JSONSerializer,
    RemoteMessageType,
)
from accessibility_toolkit.remote.routing import MessageRouter
from accessibility_toolkit.remote.session import RemoteSession
from accessibility_toolkit.remote.transport import RelayTransport, Transport
```

- [ ] **Step 2: Run remote tests and verify failure**

Run:

```bash
pytest tests/unit/test_protocol_serializer.py tests/unit/test_message_router.py tests/unit/test_remote_session.py tests/integration/test_relay_session.py -v
```

Expected: FAIL because `accessibility_toolkit.remote` is missing.

- [ ] **Step 3: Move the protocol implementation without changing wire behavior**

```bash
mkdir -p src/accessibility_toolkit/remote
git mv src/accessibility_toolkit/interop/protocol/connection_info.py src/accessibility_toolkit/remote/connection.py
git mv src/accessibility_toolkit/interop/protocol/messages.py src/accessibility_toolkit/remote/messages.py
git mv src/accessibility_toolkit/interop/protocol/serializer.py src/accessibility_toolkit/remote/serializer.py
git mv src/accessibility_toolkit/interop/protocol/events.py src/accessibility_toolkit/remote/events.py
git mv src/accessibility_toolkit/interop/protocol/routing src/accessibility_toolkit/remote/routing
git mv src/accessibility_toolkit/interop/protocol/session src/accessibility_toolkit/remote/session
git mv src/accessibility_toolkit/interop/protocol/transport src/accessibility_toolkit/remote/transport
```

Preserve message enum values, serializer payloads, event dataclasses, relay transport behavior, and session lifecycle. Define explicit public APIs for `remote`, `remote.routing`, `remote.session`, and `remote.transport`.

- [ ] **Step 4: Update NVDA Remote application consumers**

Update service, use-case, state, legacy bridge, and tests. Keep the legacy key payload bridge in `apps.nvda_remote`; it remains app-specific.

- [ ] **Step 5: Run remote and application tests**

Run:

```bash
pytest tests/unit/test_protocol_serializer.py tests/unit/test_message_router.py tests/unit/test_remote_session.py tests/unit/test_nvda_remote_app_service.py tests/unit/test_nvda_remote_use_cases.py tests/unit/test_nvda_remote_legacy_key_payload.py tests/unit/test_nvda_remote_legacy_key_payload_bridge.py tests/integration/test_relay_session.py -v
```

Expected: PASS.

- [ ] **Step 6: Verify the remote dependency boundary**

Run:

```bash
rg -n "accessibility_toolkit\.remote" src/accessibility_toolkit/input src/accessibility_toolkit/output src/accessibility_toolkit/scheduling src/accessibility_toolkit/interaction src/accessibility_toolkit/events
```

Expected: no matches.

- [ ] **Step 7: Commit the remote move**

```bash
git add src tests
git commit -m "refactor: consolidate toolkit remote package"
```

### Task 6: Finish Runtime Wiring and Delete Technical-Layer Packages

**Files:**

- Modify: `src/accessibility_toolkit/runtime/environment.py`
- Modify: `src/accessibility_toolkit/runtime/output.py`
- Modify: `src/accessibility_toolkit/runtime/platform.py`
- Modify: `src/accessibility_toolkit/runtime/runtime_parts.py`
- Modify: `src/accessibility_toolkit/runtime/__init__.py`
- Delete: remaining `src/accessibility_toolkit/application/`
- Delete: remaining `src/accessibility_toolkit/application_support/`
- Delete: remaining `src/accessibility_toolkit/interop/`
- Delete: remaining `src/accessibility_toolkit/adapters/`
- Add: `tests/unit/test_functional_package_api.py`
- Rename: `tests/unit/test_bootstrap_output.py` -> `tests/unit/test_runtime_output.py`
- Rename: `tests/unit/test_bootstrap_platform.py` -> `tests/unit/test_runtime_platform.py`
- Rename: `tests/unit/test_bootstrap_runtime.py` -> `tests/unit/test_runtime_environment.py`

**Interfaces:**

- Consumes: public APIs from every functional package; runtime is the only core composition layer allowed to do so.
- Produces: the existing environment helpers, platform factories, `OutputServices`, `PlatformServices`, and runtime-part builders at unchanged callable signatures.

- [ ] **Step 1: Add package API and import-boundary tests**

Cover:

- Importing each new first-level package.
- Common public symbols being present in each package's `__all__`.
- Cross-platform imports not eagerly loading Windows or macOS-only dependencies.
- Old technical-layer packages raising `ModuleNotFoundError`.
- No runtime module being imported by input, output, scheduling, interaction, events, or remote during isolated package imports.

Use a parameterized import contract in `tests/unit/test_functional_package_api.py`:

```python
import importlib
import sys

import pytest


PUBLIC_SYMBOLS = {
    "accessibility_toolkit.scheduling": {"CancellationToken", "EventCallbacks", "ScheduledFuture", "Scheduler"},
    "accessibility_toolkit.events": {"AppEvent", "ErrorRaised", "SpeechEngineChanged", "InputCaptureChanged", "HotkeyCaptureChanged", "ClipboardAvailabilityChanged", "ModeChanged"},
    "accessibility_toolkit.input": {"HID", "KeyEvent", "CapturedKeyEvent", "KeyboardInputService"},
    "accessibility_toolkit.output": {"Capabilities", "ClipboardService", "QueuedService"},
    "accessibility_toolkit.output.speech": {"SpeechSequence", "SpeechService", "SpeechEngineOption"},
    "accessibility_toolkit.interaction": {"ActivationMode", "ModeManager"},
    "accessibility_toolkit.remote": {"ConnectionInfo", "ConnectionMode", "JSONSerializer", "RemoteMessageType"},
    "accessibility_toolkit.runtime": {"AppRuntimeParts", "OutputServices", "PlatformProvider", "build_app_runtime_parts", "build_output_services"},
}


@pytest.mark.parametrize(("module_name", "expected"), PUBLIC_SYMBOLS.items())
def test_public_package_exports(module_name, expected):
    module = importlib.import_module(module_name)
    assert expected <= set(module.__all__)
    assert all(hasattr(module, name) for name in expected)


@pytest.mark.parametrize("name", ["application", "application_support", "interop", "adapters"])
def test_removed_technical_package_is_not_importable(name):
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(f"accessibility_toolkit.{name}")


@pytest.mark.parametrize("name", ["input", "output", "scheduling", "interaction", "events", "remote"])
def test_feature_import_does_not_load_runtime(name):
    sys.modules.pop("accessibility_toolkit.runtime", None)
    importlib.import_module(f"accessibility_toolkit.{name}")
    assert "accessibility_toolkit.runtime" not in sys.modules
```

- [ ] **Step 2: Finish runtime imports and remove compatibility loading**

Update all runtime imports to functional paths. Remove old/new dual-path import behavior and any cached module names based on `adapters.*`. Preserve lazy platform loading and the existing unsupported-platform fallbacks.

Define the runtime composition API explicitly in `runtime/__init__.py`:

```python
from accessibility_toolkit.runtime.output import OutputServices, build_output_services
from accessibility_toolkit.runtime.platform import PlatformProvider, PlatformServices
from accessibility_toolkit.runtime.runtime_parts import AppRuntimeParts, build_app_runtime_parts

__all__ = [
    "AppRuntimeParts",
    "OutputServices",
    "PlatformProvider",
    "PlatformServices",
    "build_app_runtime_parts",
    "build_output_services",
]
```

- [ ] **Step 3: Delete the old package trees**

Delete the four technical-layer directories after confirming every owned file has a target location. Do not leave empty package markers.

- [ ] **Step 4: Rename runtime test files and update internal aliases**

```bash
git mv tests/unit/test_bootstrap_output.py tests/unit/test_runtime_output.py
git mv tests/unit/test_bootstrap_platform.py tests/unit/test_runtime_platform.py
git mv tests/unit/test_bootstrap_runtime.py tests/unit/test_runtime_environment.py
```

Rename test modules that still use the historical `bootstrap` name. Update local aliases such as `bootstrap_output` to runtime-oriented names; behavior assertions remain unchanged.

- [ ] **Step 5: Run public API and runtime tests**

Run:

```bash
pytest tests/unit/test_functional_package_api.py tests/unit/test_runtime_output.py tests/unit/test_runtime_platform.py tests/unit/test_runtime_environment.py tests/unit/test_runtime_parts.py tests/unit/test_app_wx.py -v
```

Expected: PASS.

- [ ] **Step 6: Verify old imports and directories are absent**

Run:

```bash
test ! -d src/accessibility_toolkit/application
test ! -d src/accessibility_toolkit/application_support
test ! -d src/accessibility_toolkit/interop
test ! -d src/accessibility_toolkit/adapters
rg -n "^(from|import) accessibility_toolkit\.(application|application_support|interop|adapters)" src tests
```

Expected: all directory checks succeed and ripgrep returns no matches.

- [ ] **Step 7: Commit the hard cutover**

```bash
git add src tests
git commit -m "refactor: complete functional package cutover"
```

### Task 7: Update Packaging and Windows Bundle Paths

**Files:**

- Modify: `packages/accessibility-toolkit-core/pyproject.toml`
- Inspect only: `packages/accessibility-toolkit-wx/pyproject.toml`; no change is expected because core discovery is corrected at its own boundary
- Modify: root `pyproject.toml`
- Modify: `packaging/windows_apps.spec`
- Modify: `packaging/macos_apps.spec` if it contains affected hidden imports
- Add/modify: packaging assertions in `tests/unit/test_functional_package_api.py` or a focused packaging test

**Interfaces:**

- Consumes: final functional source paths and the package-relative NVDA DLL contract from Task 3.
- Produces: a core wheel/sdist containing only `accessibility_toolkit`, a wx wheel containing only `accessibility_toolkit_wx`, and Windows bundle metadata using the new DLL and hidden-import paths.

- [ ] **Step 1: Add static packaging assertions**

Test or explicitly verify that:

- Core discovery is `include = ["accessibility_toolkit", "accessibility_toolkit.*"]`.
- wx discovery cannot be included by the core pattern.
- Package data names `accessibility_toolkit.output.speech.windows`.
- The DLL source and destination use `output/speech/windows/vendor/nvda/x64`.
- PyInstaller hidden imports use functional package paths.

- [ ] **Step 2: Update setuptools configuration**

In the core project:

```toml
[tool.setuptools.packages.find]
where = ["../../src"]
include = ["accessibility_toolkit", "accessibility_toolkit.*"]

[tool.setuptools.package-data]
"accessibility_toolkit.output.speech.windows" = ["vendor/nvda/x64/*.dll"]
```

Apply the equivalent package-data path correction to the root development package metadata.

- [ ] **Step 3: Update PyInstaller specs**

Change the Windows DLL source, bundled destination, and hidden imports. Inspect macOS hidden imports for old package names and update them if present.

- [ ] **Step 4: Build and inspect the core distributions**

Run:

```bash
python -m build packages/accessibility-toolkit-core
python -m zipfile -l packages/accessibility-toolkit-core/dist/*.whl
```

Expected:

- The wheel contains `accessibility_toolkit/input`, `output`, `scheduling`, `interaction`, `events`, `remote`, and `runtime`.
- The wheel does not contain `accessibility_toolkit_wx` or any removed technical-layer package.
- The wheel contains the NVDA Controller DLL at the new output/speech path.

- [ ] **Step 5: Run packaging reference checks**

```bash
rg -n "adapters[./]|accessibility_toolkit\.adapters" packages packaging pyproject.toml
```

Expected: no matches.

- [ ] **Step 6: Commit packaging updates**

```bash
git add packages packaging pyproject.toml tests
git commit -m "build: package functional toolkit layout"
```

### Task 8: Update Current Documentation

**Files:**

- Modify: `README.md`
- Modify: `docs/zh_TW/README.md`
- Modify: `spec.md`
- Modify: `docs/zh_TW/spec.md`
- Modify: `docs/toolkit-package-migration-checklist.md`
- Modify: `docs/toolkit-package-migration-checklist_zh-TW.md`
- Review: other non-historical current documentation found by ripgrep

**Interfaces:**

- Consumes: the final public imports and dependency rules established in Tasks 1–7.
- Produces: current English and Traditional Chinese usage/architecture documentation; historical design records remain unchanged.

- [ ] **Step 1: Replace current architecture trees and examples**

Document the seven first-level functional packages and add short imports demonstrating input, output, scheduling, interaction, and remote usage.

- [ ] **Step 2: Explain the dependency direction**

Document that scheduling and events are foundations, interaction consumes input/events, remote consumes stable output/speech wire models, and runtime performs composition.

- [ ] **Step 3: Update or retire the old package migration checklist**

Do not leave the previous technical-layer migration checklist looking current. Either rewrite it for the new migration or mark it completed and superseded with a link to this spec and implementation plan.

- [ ] **Step 4: Keep historical Superpowers documents historical**

Do not mechanically rewrite old design/plan documents that describe the architecture at the time they were authored. Their old paths are allowed as historical context.

- [ ] **Step 5: Verify current documentation**

Search current documents for architecture descriptions and code examples that still present removed paths as usable:

```bash
rg -n "accessibility_toolkit\.(application|application_support|interop|adapters)|src/(application|interop|adapters|bootstrap)" README.md spec.md docs/zh_TW/README.md docs/zh_TW/spec.md docs/toolkit-package-migration-checklist*.md
```

Expected: no stale current API examples or architecture trees; superseded-history notes may name old paths explicitly.

- [ ] **Step 6: Commit documentation updates**

```bash
git add README.md spec.md docs
git commit -m "docs: describe functional toolkit packages"
```

### Task 9: Run Full Verification

**Files:**

- Modify only files required to resolve migration regressions discovered by verification.

**Interfaces:**

- Consumes: every deliverable from Tasks 1–8.
- Produces: evidence that imports, tests, dependency direction, distributions, bundle metadata, and documentation satisfy both specifications.

- [ ] **Step 1: Run import and namespace checks**

```bash
python -c "import accessibility_toolkit; import accessibility_toolkit.input; import accessibility_toolkit.output; import accessibility_toolkit.scheduling; import accessibility_toolkit.interaction; import accessibility_toolkit.events; import accessibility_toolkit.remote; import accessibility_toolkit.runtime"
rg -n "^(from|import) accessibility_toolkit\.(application|application_support|interop|adapters)" src tests
rg -n "adapters[./]|accessibility_toolkit\.adapters" packages packaging pyproject.toml
```

Expected: imports succeed; both ripgrep commands return no matches.

- [ ] **Step 2: Run the complete test suite**

```bash
pytest tests/unit tests/integration -v
```

Expected: PASS.

- [ ] **Step 3: Inspect dependency direction**

Use ripgrep or an import-graph tool to confirm:

- `scheduling` and `events` import no other toolkit feature package.
- No functional package imports `runtime`.
- Only runtime and application code import `remote`; within core, output/input/interaction/events/scheduling do not.
- `remote` may import `output.speech`, but output does not import remote.

Run these exact checks:

```bash
rg -n "accessibility_toolkit\.(input|output|interaction|remote|runtime)" src/accessibility_toolkit/scheduling src/accessibility_toolkit/events
rg -n "accessibility_toolkit\.runtime" src/accessibility_toolkit/input src/accessibility_toolkit/output src/accessibility_toolkit/scheduling src/accessibility_toolkit/interaction src/accessibility_toolkit/events src/accessibility_toolkit/remote
rg -n "accessibility_toolkit\.remote" src/accessibility_toolkit/input src/accessibility_toolkit/output src/accessibility_toolkit/scheduling src/accessibility_toolkit/interaction src/accessibility_toolkit/events
rg -n "accessibility_toolkit\.output\.speech" src/accessibility_toolkit/remote
```

Expected: the first three commands return no matches; the fourth returns only serializer/router wire-model imports.

- [ ] **Step 4: Validate packages and platform bundles proportionally**

- Build and inspect core and wx distributions.
- On Windows, run the existing PyInstaller command and verify the NVDA Controller DLL is bundled and loadable.
- On macOS, run the existing PyInstaller command or at minimum validate the spec and platform-import tests when a GUI build environment is unavailable.

- [ ] **Step 5: Review the final diff**

Confirm that the diff contains package movement, import changes, packaging updates, tests, and current documentation only. Confirm there are no compatibility layers and no unrelated user changes were overwritten.

- [ ] **Step 6: Commit any final migration fixes**

```bash
git add src tests packages packaging pyproject.toml README.md spec.md docs
git commit -m "test: verify functional package migration"
```
