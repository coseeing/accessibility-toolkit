# Functional Package Reorganization - Code Review Task

## Overview

Main-agent code review of the completed functional package reorganization refactor, performed commit-by-commit in chronological order (oldest to newest) against:

- **Spec:** `docs/superpowers/specs/2026-07-10-functional-package-reorganization-design.md`
- **Plan:** `docs/superpowers/plans/2026-07-10-functional-package-reorganization-implementation.md`
- **Completion report:** `docs/superpowers/finish_task.md`

## Methodology

For each commit listed in `docs/superpowers/finish_task.md`, a read-only code reviewer sub-agent evaluated the diff against the corresponding plan task and the design spec. The main agent consolidated findings, verified flagged issues independently, dispatched a fix sub-agent for every spec mismatch or bug, and re-reviewed until clean. Process skills used: `requesting-code-review` (reviewer dispatch) and `verification-before-completion` (evidence before assertions).

## Commits Under Review

| Order | Commit | Message | Spec Task |
|------:|--------|---------|-----------|
| 1 | `b6056a3` | refactor: move scheduling and events by function | Task 1 |
| 2 | `916dadb` | refactor: consolidate toolkit input package | Task 2 |
| 3 | `96124e5` | refactor: consolidate toolkit output package | Task 3 |
| 4 | `710bc01` | refactor: move mode lifecycle into interaction | Task 4 |
| 5 | `d850a72` | refactor: consolidate toolkit remote package | Task 5 |
| 6 | `cbaed7e` | refactor: complete functional package cutover | Task 6 |
| 7 | `60a38f3` | build: package functional toolkit layout | Task 7 |
| 8 | `d98ce6a` | docs: describe functional toolkit packages | Task 8 |

## Baseline Verification (pre-review)

- `import accessibility_toolkit` and all 7 functional subpackages: OK
- `pytest tests/unit tests/integration -q`: 819 passed
- Dependency direction checks: clean (see Final Verification)

## Per-Commit Review Findings

### 1. `b6056a3` - Task 1: Scheduling & Events Foundations

**Assessment: Ready to merge.**

- Both moves are pure `git mv` renames (100% similarity) with no behavior changes.
- `scheduling/__init__.py` exports exactly `CancellationToken`, `EventCallbacks`, `ScheduledFuture`, `Scheduler`; `events/__init__.py` exports the 6 lifecycle dataclasses plus `AppEvent`, both with explicit `__all__`.
- Hard cut honored: `application/output/__init__.py` dropped the scheduler exports; no shims/forwarding at old paths.
- Dependency direction clean: `scheduling/scheduler.py` imports only stdlib; `events/application.py` imports only `dataclasses`.
- All consumers updated (runtime, output services, speech backends, NVDA controller, pyttsx3, mode_manager, all 3 app entrypoints/services, both UI frames, tests). Tests renamed as specified.

**Issues:** None.

### 2. `916dadb` - Task 2: Input Domain

**Assessment: Ready to merge.**

- All required moves present; old paths (`interop/key`, `adapters/inputs`, `application/input`, relevant `adapters/windows` & `adapters/macos` input files) fully deleted.
- `input/__init__.py` has a deliberate `__all__` exposing only the cross-platform surface; does not import `input.windows`/`input.macos` (lazy).
- `input/events.py` merges `KeyEvent` + `CapturedKeyEvent` with no eager Windows import; `input/policies.py` consolidates `ActiveKeyEventPolicy` and `should_pass_through_system_toggle` with the `WindowsNativeKeyContext` import lazily inside the function body; `system_toggle_policy.py` deleted.
- Platform `input/windows/__init__.py` and `input/macos/__init__.py` exist with explicit `__all__`.
- `runtime/platform.py` dropped `_import_compat_module()`; lazy platform loading preserved.
- No behavior changes; enum values, dataclass shapes, and decision logic identical.
- `input` imports nothing from `remote`, `runtime`, or `scheduling`. Tests renamed/updated incl. monkeypatch strings and fake `sys.modules` keys.

**Issues (transient, resolved by Task 6):**
- Minor: stale `adapters/macos/__init__.py` with `__all__ = ["keymap","permissions"]` pointing at moved submodules. Deleted in the Task 6 cutover (`cbaed7e`); not present at HEAD.

### 3. `96124e5` - Task 3: Output & Speech

**Assessment: Ready to merge.**

- All required moves present; old locations fully removed; `adapters/outputs/ref𦳒.txt` deleted.
- `output/queue.py` (renamed from `service.py`) preserves `Mode.SEQUENTIAL`/`Mode.PARALLEL` enum values and `QueuedService` behavior.
- NVDA controller correct: `VENDORED_X64_DLL = Path(__file__).resolve().parent / "vendor"/"nvda"/"x64"/"nvdaControllerClient.dll"`; imports only `output.speech.*` and `scheduling`; no `runtime`. DLL relocated to `output/speech/windows/vendor/nvda/x64/`. Tests monkeypatch `VENDORED_X64_DLL` and assert `runtime` is not loaded during isolated import.
- Explicit `__all__` for `output`, `output.speech`, `output.speech.windows`, `output.windows` (plus `output.speech.drivers`).
- Dependency direction clean: nothing under `output/` imports `remote`/`runtime`; interop serializer/routing now import wire models from `output.speech` (intended `remote -> output.speech` edge).
- Lazy platform loading preserved in `runtime/platform.py`. No behavior/schema change (persisted engine IDs, JSON schema, `clamp_percent` semantics intact).

**Issues (transient/out-of-scope, non-blocking):**
- Minor: `packaging/macos_apps.spec` hidden-imports migrated to `input.macos.*` in this commit (an input-reorg fix shipped with the output task). Correct and necessary; purely a commit-scoping note.
- Minor: stale `adapters/macos/__init__.py` (same as Task 2); deleted in Task 6.

### 4. `710bc01` - Task 4: Interaction Modes

**Assessment: Ready to merge.**

- Clean rename `application_support/mode_manager.py` -> `interaction/modes.py` with `ActivationMode` protocol merged in verbatim from `mode_types.py`; `mode_types.py` deleted.
- `interaction/__init__.py` exports exactly `ActivationMode`, `ModeManager` with explicit `__all__`.
- Imports updated to `accessibility_toolkit.{input,events}`; no forbidden imports (remote/runtime/platform/speech/wx/dll) in `interaction`.
- Behavior preserved verbatim. App services switched to the new import; app-specific modes remain app-side.

**Issues (fixed in Round 1):**
- Minor: unused `ActivationMode` import in `tests/unit/test_mode_manager.py:5`. Fixed (see Round 1 fixes).

### 5. `d850a72` - Task 5: Remote Domain

**Assessment: Ready to merge with fixes (applied in Round 1).**

- All required moves present; subpackage `__init__.py` files created with explicit `__all__` (`remote.routing` -> `MessageRouter`; `remote.session` -> `RemoteSession`; `remote.transport` -> `Transport`,`RelayTransport`).
- Dependency boundary respected: no other feature package imports `remote`; `remote` imports `output.speech` only for wire-format models (`SpeechSequence` in `message_router.py`, `restore_sequence_items` in `serializer.py`).
- Behavior preserved (enum values, payloads, event dataclasses, relay transport, session lifecycle unchanged). NVDA Remote app + tests updated; legacy key payload bridge kept app-side.

**Issues:**
- Critical (transient, resolved by Task 6): `interop/protocol/__init__.py` left as a forwarding shim re-exporting from `accessibility_toolkit.remote.*`. The spec forbids shims. Deleted in the Task 6 cutover; not present at HEAD.
- Important (fixed in Round 1): The spec's documented canonical usage `from accessibility_toolkit.remote import RemoteSession` (spec L292) raised `ImportError` because `remote/__init__.py` did not re-export `RemoteSession` (the plan scoped it to `remote.session`). Fixed by re-exporting `RemoteSession` from `remote/__init__.py`.
- Minor (not fixed, additive/harmless): `remote/events.py` added `RemotePeerEvent`/`RemoteProtocolError` type aliases beyond the plan; `RemoteSessionVersionMismatch` not in `remote/__init__.py`'s `__all__`. Documented as a recommendation.

### 6. `cbaed7e` - Task 6: Cutover & Delete Old Packages

**Assessment: Ready to merge.**

- `runtime/__init__.py` defines exactly the 6 composition symbols (`AppRuntimeParts`, `OutputServices`, `PlatformProvider`, `PlatformServices`, `build_app_runtime_parts`, `build_output_services`) with matching `__all__`.
- All 4 technical-layer packages fully deleted including nested markers (`interop/protocol/__init__.py`, `adapters/macos/__init__.py`, `adapters/windows/__init__.py`). `git ls-tree HEAD` confirms 0 tracked files under `application`/`application_support`/`interop`/`adapters`.
- `test_functional_package_api.py` covers all 8 `PUBLIC_SYMBOLS` mappings (subset check), the removed-package test (4 names), and the feature-not-loading-runtime test (6 names) — matching the plan.
- Test renames done; only behavioral edit is `bootstrap_output` -> `runtime_output` alias (3 sites), assertions unchanged.
- Runtime modules import exclusively via functional paths; lazy platform loading and unsupported-platform null fallbacks preserved.

**Issues (environment, not a commit defect):**
- The working tree retained leftover `__pycache__`-only directories under the 4 old package paths (untracked/gitignored), which Python treated as namespace packages, causing `test_removed_technical_package_is_not_importable` to fail (815 passed / 4 failed) and contradicting the finish-task claim of 819/819. These contain no source files (verified). Removed by the main agent as environment hygiene; the commit itself is correct.

### 7. `60a38f3` - Task 7: Packaging

**Assessment: Ready to merge.**

- Core `pyproject.toml` discovery changed to exactly `include = ["accessibility_toolkit", "accessibility_toolkit.*"]` (correctly excludes `accessibility_toolkit_wx`).
- Package-data corrected in both core and root metadata to `accessibility_toolkit.output.speech.windows` -> `vendor/nvda/x64/*.dll`.
- `packaging/windows_apps.spec` DLL source and destination use `output/speech/windows/vendor/nvda/x64`; all hidden imports are functional paths and resolve via `importlib.find_spec`; no `adapters` references remain.
- macOS spec already migrated in Task 3; correctly left untouched.
- wx package unaffected by the core discovery change. Reference checks clean. Static assertions added and passing.

**Issues (not fixed, recommendations):**
- Minor: static packaging assertions cover `pyproject.toml` but not `packaging/windows_apps.spec`; a future edit could regress the spec to `adapters` paths with no test failure. Recommendation: add a spec-file guard.
- Minor: discovery assertion checks list membership rather than asserting the exact `include == ["accessibility_toolkit", "accessibility_toolkit.*"]`.

### 8. `d98ce6a` - Task 8: Documentation

**Assessment: Ready to merge with fixes (applied in Round 1).**

- `README.md` & `docs/zh_TW/README.md`: new 7-package tree; dependency-direction paragraph; import examples cover input, output, output.speech, scheduling, interaction, remote.
- `spec.md` & `docs/zh_TW/spec.md` §8: rewritten to the functional structure with per-package responsibilities; old `src/adapters|application|bootstrap|interop` bullets removed.
- Historical Superpowers design/plan docs untouched. Verification grep on README/spec (both locales): no stale current-API references.

**Issues:**
- Important (fixed in Round 1): `docs/toolkit-package-migration-checklist.md` and `_zh-TW.md` still had 129 unchecked `- [ ]` actionable items looking current despite a "COMPLETED/SUPERSEDED" banner. Plan Task 8 Step 3 requires the checklist not look current. Fixed by flipping all items to `- [x]`.
- Minor (fixed in Round 1): `spec.md:357` duplicated "The key principle is" phrase. Collapsed to a single sentence.
- Minor (not fixed): README tree comment for `output/` ("Output scheduling and queued services") vs `scheduling/` could be clearer. Documented as a recommendation.

## Review Rounds

### Round 1 - Initial Review (all 8 commits)

Dispatched 8 read-only reviewer sub-agents (2 parallel batches of 4). Consolidated findings:

| Severity | Count | Status |
|----------|------:|--------|
| Critical (transient) | 1 | Resolved by Task 6 cutover (`interop/protocol/__init__.py` shim deleted) |
| Important | 2 | Fixed via fix sub-agent |
| Minor (fixed) | 2 | Fixed via fix sub-agent |
| Minor (recommendations) | 4 | Documented; not blocking |
| Environment | 1 | Leftover `__pycache__`-only dirs cleaned by main agent |

**Important issues fixed:**
1. `from accessibility_toolkit.remote import RemoteSession` raised `ImportError` (spec L292 documented usage). Re-exported `RemoteSession` from `remote/__init__.py`.
2. Migration checklists (EN + zh-TW) had 129 unchecked actionable items. Flipped all to `- [x]`.

**Minor issues fixed:**
3. Unused `ActivationMode` import removed from `tests/unit/test_mode_manager.py`.
4. Duplicated "The key principle is" phrase collapsed in `spec.md:357`.

**Fix sub-agent scope (5 files, verified by main agent):**
- `src/accessibility_toolkit/remote/__init__.py` (+`RemoteSession` import & `__all__` entry)
- `docs/toolkit-package-migration-checklist.md` (129 `[ ]` -> `[x]`)
- `docs/toolkit-package-migration-checklist_zh-TW.md` (129 `[ ]` -> `[x]`)
- `tests/unit/test_mode_manager.py` (drop unused import)
- `spec.md` (collapse duplicated phrase)

### Round 2 - Re-review (after fixes)

Main agent independently verified every fix against the working tree:

- `git diff --stat`: exactly the 5 intended files; no collateral changes.
- Full suite: `pytest tests/unit tests/integration -q` -> **819 passed, 0 failed**.
- `from accessibility_toolkit.remote import RemoteSession` -> OK; `RemoteSession` in `remote.__all__`.
- Checklists: 0 unchecked, 129 checked (both EN & zh-TW).
- `spec.md`: exactly 1 "The key principle is" phrase.
- `test_mode_manager.py`: 0 `ActivationMode` references.
- Dependency direction re-verified clean (the `RemoteSession` re-export introduced no forbidden imports): `test_feature_import_does_not_load_runtime` -> 6 passed; no feature package imports `runtime` or `remote`; `remote` imports `output.speech` only for wire models.

**Verdict: Clean.** No remaining Critical or Important issues. The review loop converged in 2 rounds.

## Final Verification (HEAD + applied fixes)

```
PYTHONPATH=src .venv/bin/python -c "import accessibility_toolkit; import accessibility_toolkit.input; \
  import accessibility_toolkit.output; import accessibility_toolkit.scheduling; \
  import accessibility_toolkit.interaction; import accessibility_toolkit.events; \
  import accessibility_toolkit.remote; import accessibility_toolkit.runtime; \
  from accessibility_toolkit.remote import RemoteSession; print('imports ok')"
-> imports ok

PYTHONPATH=src .venv/bin/python -m pytest tests/unit tests/integration -q
-> 819 passed in 1.84s
```

Dependency direction (ripgrep/grep):

| Check | Result |
|-------|--------|
| `scheduling`/`events` import no feature package | no matches (clean) |
| No feature package imports `runtime` | no matches (clean) |
| No feature package (other than runtime) imports `remote` | no matches (clean) |
| `remote` imports `output.speech` only for wire models | 2 matches (serializer, message_router) - allowed |
| `^(from\|import) accessibility_toolkit.(application\|application_support\|interop\|adapters)` in `src`/`tests` | 0 matches |
| `adapters[./]\|accessibility_toolkit.adapters` in `packages`/`packaging`/`pyproject.toml` | 0 matches |
| Old package dirs exist under `src/accessibility_toolkit/` | none (only the 7 functional packages + root `__init__.py`) |

## Recommendations (non-blocking, for future work)

1. **PyInstaller spec guard (Task 7):** Add a static test asserting `packaging/windows_apps.spec` hidden imports and DLL paths use functional paths and contain no `adapters` references, so a hand-edit cannot silently regress.
2. **Discovery assertion tightness (Task 7):** Assert `include == ["accessibility_toolkit", "accessibility_toolkit.*"]` exactly rather than list membership.
3. **`remote` event API surface (Task 5):** Decide whether `RemotePeerEvent`/`RemoteProtocolError` type aliases and `RemoteSessionVersionMismatch` are public; either re-export consistently from `remote/__init__.py` or document them as implementation paths.
4. **README tree wording (Task 8):** Clarify the distinction between `output/` (output queueing) and `scheduling/` (shared runtime scheduler) in the package tree comment.
5. **Environment hygiene:** Leftover `__pycache__` directories under deleted package paths can resurrect namespace packages and break `test_removed_technical_package_is_not_importable`. Consider a `conftest` cleanup or asserting the old dirs are absent at session start.

## Final Assessment

**Ready to merge: Yes (with the applied review fixes).**

All 8 commits faithfully implement their corresponding plan tasks and satisfy the design spec. Two Important spec-compliance gaps (the `remote.RemoteSession` public re-export and the migration-checklist "looking current" issue) and two minor issues were fixed during the review; the full suite passes (819/819), dependency direction is clean, old namespaces are gone, and packaging metadata is correct. Remaining items are non-blocking recommendations.
