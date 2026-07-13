# Toolkit Package Migration Plan

## Goal

Restructure this repository so the shared accessibility functionality becomes independently publishable Python packages, while application-specific code remains in separate app modules or repos.

The target is not only to "move shared code out of `apps/`", but to establish clear package boundaries, stable dependency direction, and a publishable package layout that can support future accessibility applications.

## Scope

This plan covers:

- shared runtime, domain, protocol, and platform integration code
- optional desktop UI support code built on `wxPython`
- separation of app-specific features from reusable toolkit code
- packaging and release structure for independently publishable packages

This plan does not include:

- rewriting app behavior
- changing protocol behavior for `nvda_remote`
- extracting `access8graph`, `key_echo`, or `nvda_remote` into separate repositories yet

## Current State

The repository already has a useful architectural split, but the package boundaries are not yet aligned with publishable artifacts:

- `src/application`
  - shared application services and orchestration
- `src/interop`
  - shared models and protocol contracts
- `src/adapters`
  - platform-specific and output/input integrations
- `src/bootstrap`
  - runtime assembly helpers
- `src/apps/shared`
  - app-level shared helpers, currently misplaced for publishing
- `src/ui/shared`
  - reusable `wxPython` desktop shell pieces
- `src/apps/*`
  - app-specific behavior
- `src/ui/*`
  - app-specific UI entrypoints and frames

The main issue is that "shared" code currently spans multiple architectural levels:

- core toolkit logic
- runtime/bootstrap helpers
- app support helpers
- optional desktop UI helpers

Those need to become separate publishable surfaces.

## Target Package Structure

### Package 1: `accessibility-toolkit-core`

Purpose:
- publish the reusable, non-UI, cross-application toolkit foundation

Contents:
- `application`
- `interop`
- `adapters`
- `bootstrap` or a renamed equivalent such as `runtime`

Suggested namespace:

```text
src/accessibility_toolkit/
    application/
    interop/
    adapters/
    runtime/
```

Notes:
- `bootstrap` should be renamed to `runtime` or `bootstrap` under the new package namespace for consistency.
- This package should contain no app-specific behavior.
- This package may still include platform adapters with optional dependencies and conditional imports.

### Package 2: `accessibility-toolkit-wx`

Purpose:
- publish optional `wxPython` desktop shell helpers for toolkit-based apps

Contents:
- reusable code from `ui/shared`
- any UI-facing controller/facade that is genuinely reusable across apps

Suggested namespace:

```text
src/accessibility_toolkit_wx/
    shell/
    speech/
    tray/
```

Candidate modules to migrate here:
- `ui/shared/panel_controller.py`
- `ui/shared/tool_app_shell.py`
- `ui/shared/speech_controls.py`
- `ui/shared/speech_settings_frame.py`
- `ui/shared/tray_icon.py`

Notes:
- This package must depend on `accessibility-toolkit-core`.
- `wxPython` should be an explicit dependency of this package, not of the core package unless the core still truly requires it.

### App Packages or App Modules

Purpose:
- keep application-specific behavior isolated from the toolkit

Contents:
- `apps/nvda_remote`
- `apps/key_echo`
- `apps/access8graph`
- `ui/nvda_remote`
- `ui/echo`
- `ui/access8graph`

Possible future packaging:
- `accessibility-toolkit-app-key-echo`
- `accessibility-toolkit-app-nvda-remote`
- `accessibility-toolkit-app-access8graph`

For the first migration, these can remain in the same repository as internal apps using the published toolkit packages.

## Module Mapping

### Move into `accessibility-toolkit-core`

Current:
- `src/application/**`
- `src/interop/**`
- `src/adapters/**`
- `src/bootstrap/**`

Target:
- `src/accessibility_toolkit/application/**`
- `src/accessibility_toolkit/interop/**`
- `src/accessibility_toolkit/adapters/**`
- `src/accessibility_toolkit/runtime/**`

### Move into `accessibility-toolkit-wx`

Current:
- `src/ui/shared/**`

Target:
- `src/accessibility_toolkit_wx/**`

### Rehome support modules currently in `apps/shared`

These should not remain under `apps`.

#### `apps/shared/mode_manager.py`

Recommendation:
- move to `accessibility_toolkit/application_support/mode_manager.py`

Reason:
- reusable interaction support logic
- not tied to any one app
- not UI-specific

#### `apps/shared/speech_runtime_settings.py`

Recommendation:
- move to `accessibility_toolkit/runtime/speech_settings.py`
  or
- move to `accessibility_toolkit/application_support/speech_runtime_settings.py`

Reason:
- integration helper that coordinates config persistence with runtime speech service
- reusable, but not domain core

#### `apps/shared/speech_settings_facade.py`

Recommendation:
- move to `accessibility_toolkit/application_support/speech_settings_facade.py`
  or to `accessibility_toolkit_wx` if it remains primarily UI-facing

Reason:
- this is a controller/facade for presentation-layer interaction
- useful across apps, but not part of low-level toolkit primitives

## Dependency Rules

The migration should enforce these dependency directions:

1. `accessibility-toolkit-core`
   - must not import any app module
   - should not depend on `wxPython`

2. `accessibility-toolkit-wx`
   - may depend on `accessibility-toolkit-core`
   - must not depend on specific apps

3. app modules/packages
   - may depend on `accessibility-toolkit-core`
   - may depend on `accessibility-toolkit-wx`
   - must not be imported by toolkit packages

4. platform-specific adapters
   - remain inside toolkit packages
   - should keep lazy imports and optional dependency behavior

## Packaging Strategy

## Phase 0 packaging target

Keep one repository, but produce at least two distributable packages:

- `accessibility-toolkit-core`
- `accessibility-toolkit-wx`

This can be implemented by:

- a monorepo with multiple `pyproject.toml` package roots
- or a single top-level build system with subpackage build configuration

Recommended approach:
- use a monorepo layout with separate package directories under `packages/`

Suggested structure:

```text
packages/
    accessibility-toolkit-core/
        pyproject.toml
        src/accessibility_toolkit/...
    accessibility-toolkit-wx/
        pyproject.toml
        src/accessibility_toolkit_wx/...
src/apps/...
src/ui/...
tests/...
```

Reason:
- package responsibilities become explicit
- release versioning can be separated later
- app code can migrate gradually without forcing repo split now

## Proposed Migration Phases

### Phase 1: Define package boundaries without behavior changes

Tasks:
- create `docs/toolkit-package-migration-plan.md`
- approve package names and namespaces
- decide whether `bootstrap` becomes `runtime` or remains `bootstrap`
- decide whether `speech_settings_facade` belongs in core support or `wx` package

Deliverable:
- approved package map and dependency rules

### Phase 2: Introduce new namespaces in place

Tasks:
- create new package roots:
  - `src/accessibility_toolkit/`
  - `src/accessibility_toolkit_wx/`
- move shared modules from:
  - `application` -> `accessibility_toolkit/application`
  - `interop` -> `accessibility_toolkit/interop`
  - `adapters` -> `accessibility_toolkit/adapters`
  - `bootstrap` -> `accessibility_toolkit/runtime`
- move `apps/shared` modules into:
  - `accessibility_toolkit/application_support`
  - or `accessibility_toolkit_wx`
- move `ui/shared` into `accessibility_toolkit_wx`

Constraints:
- avoid changing behavior while moving modules
- update imports incrementally
- keep tests green after each sub-step

Deliverable:
- repository compiles and tests pass under new namespaces

### Phase 3: Add compatibility shims

Tasks:
- keep temporary compatibility modules in old paths where needed
- re-export from old modules to new modules during transition

Examples:
- old `application` package imports from `accessibility_toolkit.application`
- old `ui.shared` imports from `accessibility_toolkit_wx`

Reason:
- reduces migration blast radius
- lets app code move gradually
- makes review and rollback easier

Deliverable:
- old imports still work temporarily

### Phase 4: Update app entrypoints and app internals

Tasks:
- update all app modules to import from new package namespaces
- remove direct imports from legacy shared locations

Primary files affected:
- `src/apps/nvda_remote/main.py`
- `src/apps/key_echo/main.py`
- `src/apps/access8graph/main.py`
- services importing `apps.shared.mode_manager`
- UI app entrypoints importing `ui.shared.*`

Deliverable:
- apps depend only on toolkit package namespaces, not legacy paths

### Phase 5: Split packaging metadata

Tasks:
- create `pyproject.toml` for `accessibility-toolkit-core`
- create `pyproject.toml` for `accessibility-toolkit-wx`
- move package data declarations for the NVDA DLL into the core package
- define optional dependencies where appropriate

Recommended dependency split:

For `accessibility-toolkit-core`:
- base dependencies only
- platform extras for macOS dependencies
- optional speech extras if needed

For `accessibility-toolkit-wx`:
- dependency on `accessibility-toolkit-core`
- `wxPython`

Deliverable:
- both packages can build wheel and sdist independently

### Phase 6: Test package installation flows

Tasks:
- install `accessibility-toolkit-core` alone and verify importability
- install `accessibility-toolkit-core` plus `accessibility-toolkit-wx`
- run app entrypoints against installed packages rather than repo-relative imports
- validate Windows DLL packaging path

Validation:
- `pip install -e packages/accessibility-toolkit-core`
- `pip install -e packages/accessibility-toolkit-wx`
- run focused unit tests
- run full test suite

Deliverable:
- package install and runtime behavior verified

### Phase 7: Remove legacy shims

Tasks:
- remove old top-level package aliases once all imports are updated
- remove dead compatibility files
- update README and developer docs to use published package imports

Deliverable:
- clean final package layout with no duplicate import paths

## Detailed Technical Decisions

### 1. Rename top-level packages under a single vendor namespace

Current top-level modules such as `application`, `interop`, and `adapters` are too generic for publication.

Recommendation:
- nest them under `accessibility_toolkit`

Reason:
- avoids import collisions
- makes published API clearer
- creates a stable namespace for future expansion

### 2. Keep support-layer code separate from core primitives

Not all reusable code belongs in the same package layer.

Recommended split:
- core primitives and services:
  - `accessibility_toolkit.application`
  - `accessibility_toolkit.interop`
  - `accessibility_toolkit.adapters`
- runtime and assembly:
  - `accessibility_toolkit.runtime`
- app support:
  - `accessibility_toolkit.application_support`
- optional desktop UI:
  - `accessibility_toolkit_wx`

### 3. Avoid app imports from toolkit packages

Toolkit packages must not import:
- `apps.nvda_remote`
- `apps.key_echo`
- `apps.access8graph`
- app-specific UI modules

Any code that needs app-specific callbacks should receive them as arguments or ports.

### 4. Reassess current dependency footprint

The current root package depends on:
- `wxPython`
- `pyinstaller`
- `pyttsx3`
- macOS `pyobjc` packages

For publishable packages:
- `pyinstaller` should not be a runtime dependency of the toolkit package
- `wxPython` should move to the optional UI package
- platform dependencies should be optional or platform-scoped

Recommended direction:

`accessibility-toolkit-core`
- `pyttsx3`
- macOS `pyobjc` markers if required by bundled adapters

`accessibility-toolkit-wx`
- `wxPython`
- dependency on `accessibility-toolkit-core`

App packaging or build tooling
- `pyinstaller`

## Risks

### Import churn

Large-scale renames will touch many files and tests.

Mitigation:
- move in phases
- use compatibility shims temporarily
- update tests with each phase

### Layer leakage

Some modules currently mix runtime coordination and UI-oriented behavior.

Mitigation:
- classify each moved module before relocation
- avoid forcing ambiguous modules into core

### Packaging regressions on Windows

The NVDA DLL packaging path must remain correct after moving `adapters.windows`.

Mitigation:
- test wheel contents
- test runtime loading on Windows
- keep package data declarations close to the new core package

### Optional dependency breakage

Platform-specific imports may fail if package boundaries change incorrectly.

Mitigation:
- preserve lazy import patterns in adapters
- validate import behavior on non-Windows and non-macOS environments

## Initial Task Breakdown

The recommended first implementation sequence is:

1. approve this migration plan
2. choose final names for:
   - `accessibility_toolkit.runtime` vs `accessibility_toolkit.bootstrap`
   - `accessibility_toolkit.application_support`
   - `accessibility_toolkit_wx`
3. create new package directories and move core modules
4. add compatibility shims
5. migrate `apps/shared`
6. migrate `ui/shared`
7. update app imports
8. split packaging metadata
9. verify install and test workflows
10. remove compatibility shims

## Recommended Decisions To Confirm

These should be confirmed before code migration begins:

1. Core package name
   - recommended: `accessibility-toolkit-core`

2. Core Python namespace
   - recommended: `accessibility_toolkit`

3. UI package name
   - recommended: `accessibility-toolkit-wx`

4. UI Python namespace
   - recommended: `accessibility_toolkit_wx`

5. Runtime package naming
   - recommended internal module name: `runtime`

6. Support-layer placement
   - recommended: `accessibility_toolkit.application_support`

## Success Criteria

The migration is complete when:

- shared non-app code is importable from publishable toolkit namespaces
- toolkit packages do not import app modules
- optional `wxPython` UI helpers are isolated from the core package
- app code depends on toolkit packages instead of legacy shared paths
- wheels and sdists can be built for the shared packages
- tests pass using the new package layout

## Next Step After Approval

After this plan is approved, the next implementation document should be a concrete execution checklist with file-by-file moves and import rewrite batches.
