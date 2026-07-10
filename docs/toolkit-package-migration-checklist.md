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

- [ ] Keep behavior unchanged for every move batch.
- [ ] Run the smallest relevant tests after each move batch.
- [ ] Update app imports after the new namespaces are stable.
- [ ] Use compatibility shims for old paths during the transition, then remove them after all app imports are updated.
- [ ] Toolkit packages must not import `apps.*` or app-specific `ui.*`.
- [ ] `accessibility-toolkit-core` must not depend on `wxPython`.

## Phase 0: Freeze Decisions

- [ ] Confirm the core distribution name is `accessibility-toolkit-core`.
- [ ] Confirm the core Python namespace is `accessibility_toolkit`.
- [ ] Confirm the UI distribution name is `accessibility-toolkit-wx`.
- [ ] Confirm the UI Python namespace is `accessibility_toolkit_wx`.
- [ ] Confirm `bootstrap` will be named `accessibility_toolkit.runtime` after migration.
- [ ] Confirm the app support layer is named `accessibility_toolkit.application_support`.
- [ ] Confirm `speech_settings_facade` starts in `accessibility_toolkit.application_support`, and only moves to `accessibility_toolkit_wx` later if it proves to serve wx UI only.

Validation:

```bash
rg -n "app_support|application_support" docs
```

## Phase 1: Create New Namespace Skeletons

- [ ] Create `src/accessibility_toolkit/__init__.py`.
- [ ] Create `src/accessibility_toolkit/application/`.
- [ ] Create `src/accessibility_toolkit/interop/`.
- [ ] Create `src/accessibility_toolkit/adapters/`.
- [ ] Create `src/accessibility_toolkit/runtime/`.
- [ ] Create `src/accessibility_toolkit/application_support/`.
- [ ] Create `src/accessibility_toolkit_wx/__init__.py`.
- [ ] Create `src/accessibility_toolkit_wx/shell/`.
- [ ] Create `src/accessibility_toolkit_wx/speech/`.
- [ ] Create `src/accessibility_toolkit_wx/tray/`.

Validation:

```bash
PYTHONPATH=src python -c "import accessibility_toolkit; import accessibility_toolkit_wx"
```

## Phase 2: Move Core Modules

### 2.1 Move `application`

- [ ] Move `src/application/**` to `src/accessibility_toolkit/application/**`.
- [ ] Update internal imports in the new location from `application.` to `accessibility_toolkit.application.`.
- [ ] Update internal imports in the new location from `interop.` to `accessibility_toolkit.interop.`.
- [ ] Update internal imports in the new location from `adapters.` to `accessibility_toolkit.adapters.`.
- [ ] Add compatibility shims under the old `src/application/**` path.

Suggested validation:

```bash
PYTHONPATH=src pytest tests/unit/test_application_events.py tests/unit/test_keyboard_input_service.py tests/unit/test_output_service.py -v
```

### 2.2 Move `interop`

- [ ] Move `src/interop/**` to `src/accessibility_toolkit/interop/**`.
- [ ] Update internal imports in the new location from `interop.` to `accessibility_toolkit.interop.`.
- [ ] Add compatibility shims under the old `src/interop/**` path.

Suggested validation:

```bash
PYTHONPATH=src pytest tests/unit/test_hid_keys.py tests/unit/test_protocol_serializer.py tests/unit/test_remote_session.py tests/unit/test_speech_commands.py -v
```

### 2.3 Move `adapters`

- [ ] Move `src/adapters/**` to `src/accessibility_toolkit/adapters/**`.
- [ ] Confirm `src/adapters/windows/vendor/nvda/x64/nvdaControllerClient.dll` has moved to the new package data path.
- [ ] Update internal imports in the new location from `adapters.` to `accessibility_toolkit.adapters.`.
- [ ] Update internal imports in the new location from `application.` to `accessibility_toolkit.application.`.
- [ ] Update internal imports in the new location from `interop.` to `accessibility_toolkit.interop.`.
- [ ] Preserve the lazy import behavior in Windows and macOS adapters.
- [ ] Add compatibility shims under the old `src/adapters/**` path.

Suggested validation:

```bash
PYTHONPATH=src pytest tests/unit/test_windows_adapters.py tests/unit/test_macos_adapters.py tests/unit/test_json_speech_settings_store.py tests/unit/test_tone_output.py -v
```

### 2.4 Move `bootstrap` to `runtime`

- [ ] Move `src/bootstrap/runtime.py` to `src/accessibility_toolkit/runtime/runtime.py`, or rename it to a clearer module name.
- [ ] Move `src/bootstrap/output.py` to `src/accessibility_toolkit/runtime/output.py`.
- [ ] Move `src/bootstrap/platform.py` to `src/accessibility_toolkit/runtime/platform.py`.
- [ ] Move `src/bootstrap/app_runtime.py` to `src/accessibility_toolkit/runtime/app_runtime.py`.
- [ ] Update internal imports in the new location to use `accessibility_toolkit.*`.
- [ ] Add compatibility shims under the old `src/bootstrap/**` path.

Suggested validation:

```bash
PYTHONPATH=src pytest tests/unit/test_bootstrap_runtime.py tests/unit/test_bootstrap_output.py tests/unit/test_bootstrap_platform.py tests/unit/test_bootstrap_app_runtime.py -v
```

## Phase 3: Move `apps/shared` to Application Support

- [ ] Move `src/apps/shared/mode_manager.py` to `src/accessibility_toolkit/application_support/mode_manager.py`.
- [ ] Move `src/apps/shared/speech_runtime_settings.py` to `src/accessibility_toolkit/application_support/speech_runtime_settings.py`.
- [ ] Move `src/apps/shared/speech_settings_facade.py` to `src/accessibility_toolkit/application_support/speech_settings_facade.py`.
- [ ] Create `src/accessibility_toolkit/application_support/__init__.py` and re-export public classes.
- [ ] Update internal imports in the new location to use `accessibility_toolkit.application.*`.
- [ ] Add compatibility shims under the old `src/apps/shared/**` path.

Suggested validation:

```bash
PYTHONPATH=src pytest tests/unit/test_mode_manager.py tests/unit/test_speech_runtime_settings.py tests/unit/test_speech_settings_facade.py -v
```

## Phase 4: Move `ui/shared` to `accessibility_toolkit_wx`

- [ ] Move `src/ui/shared/panel_controller.py` to `src/accessibility_toolkit_wx/shell/panel_controller.py`.
- [ ] Move `src/ui/shared/tool_app_shell.py` to `src/accessibility_toolkit_wx/shell/tool_app_shell.py`.
- [ ] Move `src/ui/shared/tray_icon.py` to `src/accessibility_toolkit_wx/tray/tray_icon.py`.
- [ ] Move `src/ui/shared/speech_controls.py` to `src/accessibility_toolkit_wx/speech/speech_controls.py`.
- [ ] Move `src/ui/shared/speech_settings_frame.py` to `src/accessibility_toolkit_wx/speech/speech_settings_frame.py`.
- [ ] Create `src/accessibility_toolkit_wx/shell/__init__.py`.
- [ ] Create `src/accessibility_toolkit_wx/speech/__init__.py`.
- [ ] Create `src/accessibility_toolkit_wx/tray/__init__.py`.
- [ ] Update internal imports in the new location to use `accessibility_toolkit_wx.*`.
- [ ] Add compatibility shims under the old `src/ui/shared/**` path.

Suggested validation:

```bash
PYTHONPATH=src pytest tests/unit/test_panel_controller.py tests/unit/test_tool_app_shell.py tests/unit/test_tray_icon.py tests/unit/test_app_wx.py -v
```

## Phase 5: Update App Imports

### 5.1 Update app service imports

- [ ] Change `apps.shared.mode_manager` in `apps.nvda_remote.service` to `accessibility_toolkit.application_support.mode_manager`.
- [ ] Change `apps.shared.mode_manager` in `apps.key_echo.service` to `accessibility_toolkit.application_support.mode_manager`.
- [ ] Change `apps.shared.mode_manager` in `apps.access8graph.service` to `accessibility_toolkit.application_support.mode_manager`.
- [ ] Change `application.*`, `interop.*`, and `adapters.*` imports in app services to `accessibility_toolkit.*`.

### 5.2 Update app runtime imports

- [ ] Update imports in `src/apps/nvda_remote/main.py`.
- [ ] Update imports in `src/apps/key_echo/main.py`.
- [ ] Update imports in `src/apps/access8graph/main.py`.
- [ ] Change `apps.shared.speech_runtime_settings` to `accessibility_toolkit.application_support.speech_runtime_settings`.
- [ ] Change `apps.shared.speech_settings_facade` to `accessibility_toolkit.application_support.speech_settings_facade`.
- [ ] Change `bootstrap.*` to `accessibility_toolkit.runtime.*`.

### 5.3 Update app UI imports

- [ ] Change `ui.shared.*` imports in `ui.nvda_remote.app` to `accessibility_toolkit_wx.*`.
- [ ] Change `ui.shared.*` imports in `ui.echo.app` to `accessibility_toolkit_wx.*`.
- [ ] Change `ui.shared.*` imports in `ui.access8graph.app` to `accessibility_toolkit_wx.*`.
- [ ] Change `application.*` imports in app-specific UI to `accessibility_toolkit.application.*`.

Suggested validation:

```bash
PYTHONPATH=src pytest tests/unit/test_nvda_remote_app_service.py tests/unit/test_key_echo_app_service.py tests/unit/test_access8graph_app_service.py -v
PYTHONPATH=src pytest tests/unit/test_nvda_remote_use_cases.py tests/unit/test_key_echo_use_cases.py tests/unit/test_access8graph_use_cases.py -v
```

## Phase 6: Update Test Imports

- [ ] Change `application.*` imports in unit tests to `accessibility_toolkit.application.*`.
- [ ] Change `interop.*` imports in unit tests to `accessibility_toolkit.interop.*`.
- [ ] Change `adapters.*` imports in unit tests to `accessibility_toolkit.adapters.*`.
- [ ] Change `bootstrap.*` imports in unit tests to `accessibility_toolkit.runtime.*`.
- [ ] Change `apps.shared.*` imports in unit tests to `accessibility_toolkit.application_support.*`.
- [ ] Change `ui.shared.*` imports in unit tests to `accessibility_toolkit_wx.*`.
- [ ] Keep app-specific test imports from `apps.*` and app-specific `ui.*`.

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

- [ ] Create `packages/accessibility-toolkit-core/`.
- [ ] Create `packages/accessibility-toolkit-wx/`.
- [ ] Decide whether to move source into `packages/*/src` immediately, or keep the current `src/` namespace layout first.

Recommendation: complete the namespace migration first, then split the source root into `packages/` to reduce the size of simultaneous changes.

### 7.2 Create `accessibility-toolkit-core` metadata

- [ ] Create `packages/accessibility-toolkit-core/pyproject.toml`.
- [ ] Set the package name to `accessibility-toolkit-core`.
- [ ] Set `package-dir` to point to the core source.
- [ ] Configure package discovery to include only `accessibility_toolkit*`.
- [ ] Declare the `pyttsx3` dependency.
- [ ] Declare macOS `pyobjc` dependencies with the `sys_platform == "darwin"` marker.
- [ ] Declare NVDA DLL package data.
- [ ] Confirm `pyinstaller` is not in runtime dependencies.
- [ ] Confirm `wxPython` is not in core dependencies.

### 7.3 Create `accessibility-toolkit-wx` metadata

- [ ] Create `packages/accessibility-toolkit-wx/pyproject.toml`.
- [ ] Set the package name to `accessibility-toolkit-wx`.
- [ ] Set `package-dir` to point to the wx source.
- [ ] Configure package discovery to include only `accessibility_toolkit_wx*`.
- [ ] Declare dependency: `accessibility-toolkit-core`.
- [ ] Declare dependency: `wxPython`.

Suggested validation:

```bash
python -m build packages/accessibility-toolkit-core
python -m build packages/accessibility-toolkit-wx
```

## Phase 8: Validate Installation Flows

- [ ] Create a clean virtualenv.
- [ ] Install the core package.
- [ ] Verify `import accessibility_toolkit`.
- [ ] Verify `accessibility_toolkit.application`, `interop`, `adapters`, and `runtime` can be imported.
- [ ] Install the wx package.
- [ ] Verify `import accessibility_toolkit_wx`.
- [ ] Verify app entrypoints can be imported against installed packages.

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

- [ ] `src/` and `tests/` no longer contain old namespace imports.
- [ ] Packages can build.
- [ ] Unit tests pass.
- [ ] Integration tests pass.

Removal items:

- [ ] Remove old `src/application/**` compatibility shims.
- [ ] Remove old `src/interop/**` compatibility shims.
- [ ] Remove old `src/adapters/**` compatibility shims.
- [ ] Remove old `src/bootstrap/**` compatibility shims.
- [ ] Remove old `src/apps/shared/**` compatibility shims.
- [ ] Remove old `src/ui/shared/**` compatibility shims.

Search check:

```bash
rg -n "from (application|interop|adapters|bootstrap|apps\.shared|ui\.shared)|import (application|interop|adapters|bootstrap|apps\.shared|ui\.shared)" src tests
```

## Phase 10: Documentation and Final Acceptance

- [ ] Update installation instructions in `README.md`.
- [ ] Update app run instructions in `README.md`.
- [ ] Update project structure guidance in `AGENTS.md`.
- [ ] Update package build commands.
- [ ] Add release process notes.
- [ ] Confirm the Chinese migration documents are updated as needed.

Final validation:

```bash
PYTHONPATH=src pytest tests/unit tests/integration -v
python -m build packages/accessibility-toolkit-core
python -m build packages/accessibility-toolkit-wx
```

Completion criteria:

- [ ] Shared non-app code lives under `accessibility_toolkit`.
- [ ] Shared wx UI code lives under `accessibility_toolkit_wx`.
- [ ] App code no longer imports old shared paths.
- [ ] Toolkit packages do not import `apps.*` or app-specific `ui.*`.
- [ ] The core package does not depend on `wxPython`.
- [ ] Wheels and sdists can be built.
- [ ] Tests pass.
