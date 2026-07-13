# Toolkit Package Migration Implementation Checklist

> **STATUS: COMPLETED AND SUPERSEDED**
>
> This checklist has been superseded by the functional-package reorganization. The old technical-layer packages (`application`, `interop`, `adapters`, `bootstrap`, `apps/shared`) have been reorganized into 7 functional packages under `accessibility_toolkit`: `input`, `output`/`output.speech`, `scheduling`, `interaction`, `events`, `remote`, and `runtime`.
>
> See the design and implementation documents for the new structure:
> - `docs/superpowers/specs/2026-07-10-functional-package-reorganization-design.md`
> - `docs/superpowers/plans/2026-07-10-functional-package-reorganization-implementation.md`

## Purpose (historical)

This checklist broke `toolkit-package-migration-plan.md` into executable implementation steps. The goal was to organize shared functionality into independently publishable packages without changing existing app behavior:

- `accessibility-toolkit-core`
- `accessibility-toolkit-wx`

This document uses `accessibility_toolkit.application_support` as the support-layer namespace.

## Execution Principles

- [x] Keep behavior unchanged for every move batch.
- [x] Run the smallest relevant tests after each move batch.
- [x] Update app imports after the new namespaces are stable.
- [x] Use compatibility shims for old paths during the transition, then remove them after all app imports are updated.
- [x] Toolkit packages must not import `apps.*` or app-specific `ui.*`.
- [x] `accessibility-toolkit-core` must not depend on `wxPython`.

## Phase 0: Freeze Decisions

- [x] Confirm the core distribution name is `accessibility-toolkit-core`.
- [x] Confirm the core Python namespace is `accessibility_toolkit`.
- [x] Confirm the UI distribution name is `accessibility-toolkit-wx`.
- [x] Confirm the UI Python namespace is `accessibility_toolkit_wx`.
- [x] Confirm `bootstrap` will be named `accessibility_toolkit.runtime` after migration.
- [x] Confirm the app support layer is named `accessibility_toolkit.application_support`.
- [x] Confirm `speech_settings_facade` starts in `accessibility_toolkit.application_support`, and only moves to `accessibility_toolkit_wx` later if it proves to serve wx UI only.

Validation:

```bash
rg -n "app_support|application_support" docs
```

## Phase 1: Create New Namespace Skeletons

- [x] Create `src/accessibility_toolkit/__init__.py`.
- [x] Create `src/accessibility_toolkit/application/`.
- [x] Create `src/accessibility_toolkit/interop/`.
- [x] Create `src/accessibility_toolkit/adapters/`.
- [x] Create `src/accessibility_toolkit/runtime/`.
- [x] Create `src/accessibility_toolkit/application_support/`.
- [x] Create `src/accessibility_toolkit_wx/__init__.py`.
- [x] Create `src/accessibility_toolkit_wx/shell/`.
- [x] Create `src/accessibility_toolkit_wx/speech/`.
- [x] Create `src/accessibility_toolkit_wx/tray/`.

Validation:

```bash
PYTHONPATH=src python -c "import accessibility_toolkit; import accessibility_toolkit_wx"
```

## Phase 2: Move Core Modules

### 2.1 Move `application`

- [x] Move `src/application/**` to `src/accessibility_toolkit/application/**`.
- [x] Update internal imports in the new location from `application.` to `accessibility_toolkit.application.`.
- [x] Update internal imports in the new location from `interop.` to `accessibility_toolkit.interop.`.
- [x] Update internal imports in the new location from `adapters.` to `accessibility_toolkit.adapters.`.
- [x] Add compatibility shims under the old `src/application/**` path.

Suggested validation:

```bash
PYTHONPATH=src pytest tests/unit/test_application_events.py tests/unit/test_keyboard_input_service.py tests/unit/test_output_service.py -v
```

### 2.2 Move `interop`

- [x] Move `src/interop/**` to `src/accessibility_toolkit/interop/**`.
- [x] Update internal imports in the new location from `interop.` to `accessibility_toolkit.interop.`.
- [x] Add compatibility shims under the old `src/interop/**` path.

Suggested validation:

```bash
PYTHONPATH=src pytest tests/unit/test_hid_keys.py tests/unit/test_protocol_serializer.py tests/unit/test_remote_session.py tests/unit/test_speech_commands.py -v
```

### 2.3 Move `adapters`

- [x] Move `src/adapters/**` to `src/accessibility_toolkit/adapters/**`.
- [x] Confirm `src/adapters/windows/vendor/nvda/x64/nvdaControllerClient.dll` has moved to the new package data path.
- [x] Update internal imports in the new location from `adapters.` to `accessibility_toolkit.adapters.`.
- [x] Update internal imports in the new location from `application.` to `accessibility_toolkit.application.`.
- [x] Update internal imports in the new location from `interop.` to `accessibility_toolkit.interop.`.
- [x] Preserve the lazy import behavior in Windows and macOS adapters.
- [x] Add compatibility shims under the old `src/adapters/**` path.

Suggested validation:

```bash
PYTHONPATH=src pytest tests/unit/test_windows_adapters.py tests/unit/test_macos_adapters.py tests/unit/test_json_speech_settings_store.py tests/unit/test_tone_output.py -v
```

### 2.4 Move `bootstrap` to `runtime`

- [x] Move `src/bootstrap/runtime.py` to `src/accessibility_toolkit/runtime/runtime.py`, or rename it to a clearer module name.
- [x] Move `src/bootstrap/output.py` to `src/accessibility_toolkit/runtime/output.py`.
- [x] Move `src/bootstrap/platform.py` to `src/accessibility_toolkit/runtime/platform.py`.
- [x] Move `src/bootstrap/app_runtime.py` to `src/accessibility_toolkit/runtime/app_runtime.py`.
- [x] Update internal imports in the new location to use `accessibility_toolkit.*`.
- [x] Add compatibility shims under the old `src/bootstrap/**` path.

Suggested validation:

```bash
PYTHONPATH=src pytest tests/unit/test_bootstrap_runtime.py tests/unit/test_bootstrap_output.py tests/unit/test_bootstrap_platform.py tests/unit/test_bootstrap_app_runtime.py -v
```

## Phase 3: Move `apps/shared` to Application Support

- [x] Move `src/apps/shared/mode_manager.py` to `src/accessibility_toolkit/application_support/mode_manager.py`.
- [x] Move `src/apps/shared/speech_runtime_settings.py` to `src/accessibility_toolkit/application_support/speech_runtime_settings.py`.
- [x] Move `src/apps/shared/speech_settings_facade.py` to `src/accessibility_toolkit/application_support/speech_settings_facade.py`.
- [x] Create `src/accessibility_toolkit/application_support/__init__.py` and re-export public classes.
- [x] Update internal imports in the new location to use `accessibility_toolkit.application.*`.
- [x] Add compatibility shims under the old `src/apps/shared/**` path.

Suggested validation:

```bash
PYTHONPATH=src pytest tests/unit/test_mode_manager.py tests/unit/test_speech_runtime_settings.py tests/unit/test_speech_settings_facade.py -v
```

## Phase 4: Move `ui/shared` to `accessibility_toolkit_wx`

- [x] Move `src/ui/shared/panel_controller.py` to `src/accessibility_toolkit_wx/shell/panel_controller.py`.
- [x] Move `src/ui/shared/tool_app_shell.py` to `src/accessibility_toolkit_wx/shell/tool_app_shell.py`.
- [x] Move `src/ui/shared/tray_icon.py` to `src/accessibility_toolkit_wx/tray/tray_icon.py`.
- [x] Move `src/ui/shared/speech_controls.py` to `src/accessibility_toolkit_wx/speech/speech_controls.py`.
- [x] Move `src/ui/shared/speech_settings_frame.py` to `src/accessibility_toolkit_wx/speech/speech_settings_frame.py`.
- [x] Create `src/accessibility_toolkit_wx/shell/__init__.py`.
- [x] Create `src/accessibility_toolkit_wx/speech/__init__.py`.
- [x] Create `src/accessibility_toolkit_wx/tray/__init__.py`.
- [x] Update internal imports in the new location to use `accessibility_toolkit_wx.*`.
- [x] Add compatibility shims under the old `src/ui/shared/**` path.

Suggested validation:

```bash
PYTHONPATH=src pytest tests/unit/test_panel_controller.py tests/unit/test_tool_app_shell.py tests/unit/test_tray_icon.py tests/unit/test_app_wx.py -v
```

## Phase 5: Update App Imports

### 5.1 Update app service imports

- [x] Change `apps.shared.mode_manager` in `apps.nvda_remote.service` to `accessibility_toolkit.application_support.mode_manager`.
- [x] Change `apps.shared.mode_manager` in `apps.key_echo.service` to `accessibility_toolkit.application_support.mode_manager`.
- [x] Change `apps.shared.mode_manager` in `apps.access8graph.service` to `accessibility_toolkit.application_support.mode_manager`.
- [x] Change `application.*`, `interop.*`, and `adapters.*` imports in app services to `accessibility_toolkit.*`.

### 5.2 Update app runtime imports

- [x] Update imports in `src/apps/nvda_remote/main.py`.
- [x] Update imports in `src/apps/key_echo/main.py`.
- [x] Update imports in `src/apps/access8graph/main.py`.
- [x] Change `apps.shared.speech_runtime_settings` to `accessibility_toolkit.application_support.speech_runtime_settings`.
- [x] Change `apps.shared.speech_settings_facade` to `accessibility_toolkit.application_support.speech_settings_facade`.
- [x] Change `bootstrap.*` to `accessibility_toolkit.runtime.*`.

### 5.3 Update app UI imports

- [x] Change `ui.shared.*` imports in `ui.nvda_remote.app` to `accessibility_toolkit_wx.*`.
- [x] Change `ui.shared.*` imports in `ui.echo.app` to `accessibility_toolkit_wx.*`.
- [x] Change `ui.shared.*` imports in `ui.access8graph.app` to `accessibility_toolkit_wx.*`.
- [x] Change `application.*` imports in app-specific UI to `accessibility_toolkit.application.*`.

Suggested validation:

```bash
PYTHONPATH=src pytest tests/unit/test_nvda_remote_app_service.py tests/unit/test_key_echo_app_service.py tests/unit/test_access8graph_app_service.py -v
PYTHONPATH=src pytest tests/unit/test_nvda_remote_use_cases.py tests/unit/test_key_echo_use_cases.py tests/unit/test_access8graph_use_cases.py -v
```

## Phase 6: Update Test Imports

- [x] Change `application.*` imports in unit tests to `accessibility_toolkit.application.*`.
- [x] Change `interop.*` imports in unit tests to `accessibility_toolkit.interop.*`.
- [x] Change `adapters.*` imports in unit tests to `accessibility_toolkit.adapters.*`.
- [x] Change `bootstrap.*` imports in unit tests to `accessibility_toolkit.runtime.*`.
- [x] Change `apps.shared.*` imports in unit tests to `accessibility_toolkit.application_support.*`.
- [x] Change `ui.shared.*` imports in unit tests to `accessibility_toolkit_wx.*`.
- [x] Keep app-specific test imports from `apps.*` and app-specific `ui.*`.

Search check:

```bash
rg -n "from (application|interop|adapters|bootstrap|apps\.shared|ui\.shared)|import (application|interop|adapters|bootstrap|apps\.shared|ui\.shared)" tests src
```

Suggested validation:

```bash
PYTHONPATH=src pytest tests/unit -v
```

## Phase 7: Create Package Metadata

### 7.1 Create monorepo package directories

- [x] Create `packages/accessibility-toolkit-core/`.
- [x] Create `packages/accessibility-toolkit-wx/`.
- [x] Decide whether to move source into `packages/*/src` immediately, or keep the current `src/` namespace layout first.

Recommendation: complete the namespace migration first, then split the source root into `packages/` to reduce the size of simultaneous changes.

### 7.2 Create `accessibility-toolkit-core` metadata

- [x] Create `packages/accessibility-toolkit-core/pyproject.toml`.
- [x] Set the package name to `accessibility-toolkit-core`.
- [x] Set `package-dir` to point to the core source.
- [x] Configure package discovery to include only `accessibility_toolkit*`.
- [x] Declare the `pyttsx3` dependency.
- [x] Declare macOS `pyobjc` dependencies with the `sys_platform == "darwin"` marker.
- [x] Declare NVDA DLL package data.
- [x] Confirm `pyinstaller` is not in runtime dependencies.
- [x] Confirm `wxPython` is not in core dependencies.

### 7.3 Create `accessibility-toolkit-wx` metadata

- [x] Create `packages/accessibility-toolkit-wx/pyproject.toml`.
- [x] Set the package name to `accessibility-toolkit-wx`.
- [x] Set `package-dir` to point to the wx source.
- [x] Configure package discovery to include only `accessibility_toolkit_wx*`.
- [x] Declare dependency: `accessibility-toolkit-core`.
- [x] Declare dependency: `wxPython`.

Suggested validation:

```bash
python -m build packages/accessibility-toolkit-core
python -m build packages/accessibility-toolkit-wx
```

## Phase 8: Validate Installation Flows

- [x] Create a clean virtualenv.
- [x] Install the core package.
- [x] Verify `import accessibility_toolkit`.
- [x] Verify `accessibility_toolkit.application`, `interop`, `adapters`, and `runtime` can be imported.
- [x] Install the wx package.
- [x] Verify `import accessibility_toolkit_wx`.
- [x] Verify app entrypoints can be imported against installed packages.

Suggested validation:

```bash
python -m venv .venv-package-check
. .venv-package-check/bin/activate
pip install -e packages/accessibility-toolkit-core
pip install -e packages/accessibility-toolkit-wx
python -c "import accessibility_toolkit; import accessibility_toolkit_wx"
PYTHONPATH=src python -m apps.key_echo.main
```

Notes:
- Runtime validation for GUI apps may require a desktop environment.
- Windows needs a separate NVDA DLL loading check.

## Phase 9: Remove Compatibility Shims

Preconditions:

- [x] `src/` and `tests/` no longer contain old namespace imports.
- [x] Packages can build.
- [x] Unit tests pass.
- [x] Integration tests pass.

Removal items:

- [x] Remove old `src/application/**` compatibility shims.
- [x] Remove old `src/interop/**` compatibility shims.
- [x] Remove old `src/adapters/**` compatibility shims.
- [x] Remove old `src/bootstrap/**` compatibility shims.
- [x] Remove old `src/apps/shared/**` compatibility shims.
- [x] Remove old `src/ui/shared/**` compatibility shims.

Search check:

```bash
rg -n "from (application|interop|adapters|bootstrap|apps\.shared|ui\.shared)|import (application|interop|adapters|bootstrap|apps\.shared|ui\.shared)" src tests
```

## Phase 10: Documentation and Final Acceptance

- [x] Update installation instructions in `README.md`.
- [x] Update app run instructions in `README.md`.
- [x] Update project structure guidance in `AGENTS.md`.
- [x] Update package build commands.
- [x] Add release process notes.
- [x] Confirm the Chinese migration documents are updated as needed.

Final validation:

```bash
PYTHONPATH=src pytest tests/unit tests/integration -v
python -m build packages/accessibility-toolkit-core
python -m build packages/accessibility-toolkit-wx
```

Completion criteria:

- [x] Shared non-app code lives under `accessibility_toolkit`.
- [x] Shared wx UI code lives under `accessibility_toolkit_wx`.
- [x] App code no longer imports old shared paths.
- [x] Toolkit packages do not import `apps.*` or app-specific `ui.*`.
- [x] The core package does not depend on `wxPython`.
- [x] Wheels and sdists can be built.
- [x] Tests pass.
