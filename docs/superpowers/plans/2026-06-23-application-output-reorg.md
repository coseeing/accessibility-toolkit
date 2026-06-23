# Application Output Reorganization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize `src/application` so output-related modules live under a semantic `application.output` package with a `speech` subpackage, without changing runtime behavior.

**Architecture:** Move output orchestration modules into `src/application/output/`, move speech-specific services into `src/application/output/speech/`, and relocate `OutputManager` plus `ClipboardService` into `application.output.manager`. Keep class names stable and add package re-exports so app/bootstrap code imports from coherent package boundaries.

**Tech Stack:** Python 3, pytest, `src` layout package imports

---

### Task 1: Lock the new import surface with tests

**Files:**
- Modify: `tests/unit/test_output_service.py`

- [ ] **Step 1: Write the failing test**

```python
def test_output_package_re_exports_core_types():
    from application.output import (
        OutputCapabilities,
        OutputManager,
        OutputMode,
        OutputScheduler,
        QueuedOutputService,
    )
    from application.output.manager import ClipboardService
    from application.output.speech import (
        SpeechBackendManager,
        SpeechBackendOption,
        SpeechService,
    )

    assert OutputCapabilities is not None
    assert OutputManager is not None
    assert ClipboardService is not None
    assert OutputMode is not None
    assert OutputScheduler is not None
    assert QueuedOutputService is not None
    assert SpeechBackendManager is not None
    assert SpeechBackendOption is not None
    assert SpeechService is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_output_service.py::test_output_package_re_exports_core_types -v`
Expected: FAIL with `ModuleNotFoundError` or import error because `application.output` does not exist yet.

- [ ] **Step 3: Implement the package surface**

Create `src/application/output/__init__.py` and `src/application/output/speech/__init__.py`, then move modules into their new paths and update imports throughout `src/` and `tests/`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_output_service.py::test_output_package_re_exports_core_types -v`
Expected: PASS.

### Task 2: Rehome output orchestration modules

**Files:**
- Create: `src/application/output/__init__.py`
- Create: `src/application/output/capabilities.py`
- Create: `src/application/output/manager.py`
- Create: `src/application/output/scheduler.py`
- Create: `src/application/output/service.py`
- Delete: `src/application/output_capabilities.py`
- Delete: `src/application/output_scheduler.py`
- Delete: `src/application/output_service.py`
- Delete: `src/application/services.py`

- [ ] **Step 1: Move files into `application.output`**

Move module contents without changing behavior, then update internal imports to use sibling modules or the new `speech` subpackage.

- [ ] **Step 2: Keep package exports explicit**

Expose these symbols from `src/application/output/__init__.py`:

```python
from application.output.capabilities import OutputCapabilities
from application.output.manager import ClipboardService, OutputManager
from application.output.scheduler import (
    CancellationToken,
    OutputEventCallbacks,
    OutputFuture,
    OutputScheduler,
)
from application.output.service import OutputMode, QueuedOutputService, SpeechOutputService
```

- [ ] **Step 3: Run focused tests**

Run: `pytest tests/unit/test_output_scheduler.py tests/unit/test_output_manager.py tests/unit/test_output_service.py -v`
Expected: PASS.

### Task 3: Rehome speech-specific modules

**Files:**
- Create: `src/application/output/speech/__init__.py`
- Create: `src/application/output/speech/backends.py`
- Create: `src/application/output/speech/service.py`
- Delete: `src/application/speech_backends.py`
- Delete: `src/application/speech_service.py`

- [ ] **Step 1: Move speech modules into `application.output.speech`**

Update `SpeechService` to import `SpeechBackendManager` and `SpeechBackendOption` from `application.output.speech.backends`, and update its type-checking import to `application.output.scheduler`.

- [ ] **Step 2: Keep subpackage exports explicit**

Expose these symbols from `src/application/output/speech/__init__.py`:

```python
from application.output.speech.backends import SpeechBackendManager, SpeechBackendOption
from application.output.speech.service import SpeechService
```

- [ ] **Step 3: Run focused speech tests**

Run: `pytest tests/unit/test_speech_backends.py tests/unit/test_speech_service.py -v`
Expected: PASS.

### Task 4: Update application and adapter imports

**Files:**
- Modify: `src/apps/access8graph/main.py`
- Modify: `src/apps/access8graph/output.py`
- Modify: `src/apps/access8graph/service.py`
- Modify: `src/apps/key_echo/main.py`
- Modify: `src/apps/key_echo/service.py`
- Modify: `src/apps/nvda_remote/main.py`
- Modify: `src/apps/nvda_remote/service.py`
- Modify: `src/apps/shared/speech_settings_controller.py`
- Modify: `src/bootstrap/platform.py`
- Modify: `src/adapters/outputs/drivers/pyttsx3.py`
- Modify: `src/adapters/windows/nvda_controller.py`
- Modify: affected tests under `tests/unit/`

- [ ] **Step 1: Replace old import paths with package imports**

Use `application.output`, `application.output.manager`, and `application.output.speech` consistently. Leave `application.keyboard` and `application.input` unchanged.

- [ ] **Step 2: Run targeted regression suites**

Run: `pytest tests/unit/test_bootstrap_platform.py tests/unit/test_key_echo_app_service.py tests/unit/test_access8graph_app_service.py tests/unit/test_nvda_remote_app_service.py -v`
Expected: PASS.

### Task 5: Final verification

**Files:**
- Verify only

- [ ] **Step 1: Run the broad output-related test subset**

Run: `pytest tests/unit/test_output_scheduler.py tests/unit/test_output_manager.py tests/unit/test_output_service.py tests/unit/test_speech_backends.py tests/unit/test_speech_service.py tests/unit/test_bootstrap_platform.py tests/unit/test_key_echo_app_service.py tests/unit/test_access8graph_app_service.py tests/unit/test_nvda_remote_app_service.py -v`
Expected: PASS.

- [ ] **Step 2: Review for stale imports**

Run: `rg -n "application\\.(output_|speech_|services)" src tests`
Expected: no stale imports to removed modules.
