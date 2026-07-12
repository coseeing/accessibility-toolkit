# Functional Package Reorganization - Main Agent Review

## Review scope

This review was performed by the main agent against:

- `docs/superpowers/finish_task.md`
- `docs/superpowers/specs/2026-07-10-functional-package-reorganization-design.md`
- `docs/superpowers/plans/2026-07-10-functional-package-reorganization-implementation.md`

Only the eight commits listed in the completion report were reviewed, in chronological order. The final working tree was then checked as an integrated result. When the main agent found a bug or specification mismatch, a focused sub-agent implemented the fix; the main agent independently reviewed the resulting diff and reran the relevant verification. This continued until no blocking findings remained.

## Commit order and assessment

| Order | Commit | Plan task | Main-agent assessment |
|---:|---|---|---|
| 1 | `b6056a3` - `refactor: move scheduling and events by function` | Task 1 | Clean |
| 2 | `916dadb` - `refactor: consolidate toolkit input package` | Task 2 | Public nested-package API gap found and fixed |
| 3 | `96124e5` - `refactor: consolidate toolkit output package` | Task 3 | Clean; minor commit-scope observations only |
| 4 | `710bc01` - `refactor: move mode lifecycle into interaction` | Task 4 | Clean |
| 5 | `d850a72` - `refactor: consolidate toolkit remote package` | Task 5 | Commit-local root API gap; already fixed in the current baseline |
| 6 | `cbaed7e` - `refactor: complete functional package cutover` | Task 6 | Clean |
| 7 | `60a38f3` - `build: package functional toolkit layout` | Task 7 | Blocking sdist defect found and fixed |
| 8 | `d98ce6a` - `docs: describe functional toolkit packages` | Task 8 | Incorrect dependency/ownership documentation found and fixed |

## Per-commit review

### 1. `b6056a3` - scheduling and events

Result: clean.

- `scheduler.py` and `application.py` are pure moves with behavior unchanged.
- `accessibility_toolkit.scheduling.__all__` exports exactly `CancellationToken`, `EventCallbacks`, `ScheduledFuture`, and `Scheduler`.
- `accessibility_toolkit.events.__all__` exports `AppEvent` and all six lifecycle event dataclasses.
- Consumers were migrated to the new paths without forwarding imports at the old paths.
- `scheduling` and `events` have no dependency on another functional package.

### 2. `916dadb` - input package

Result after two fix/re-review rounds: clean.

The domain moves, policy/event merges, lazy runtime selection, and removal of compatibility loading were correct. The main agent found that `input.windows` and `input.macos` declared only module names in `__all__` and did not bind their supported platform implementations at the package root. That did not satisfy the design requirement that both nested packages expose a clear public API. The documented canonical import `from accessibility_toolkit.input.windows import WindowsKeyboardHook` also failed because the existing implementation class was named `WindowsKeyboardCapture`.

Fixes:

- Exported the existing Windows/macOS capture, mapping, event-tap, native-context, and permissions APIs from their package roots.
- Preserved `WindowsKeyboardCapture` and added `WindowsKeyboardHook` as an identity-preserving alias required by the documented API.
- Added package-root and `__all__` contract tests for both nested packages.

TDD and re-review evidence:

- First RED: 2 new public-package contracts failed; GREEN: 22 tests passed.
- Second RED: `WindowsKeyboardHook` was missing; GREEN plus platform/runtime tests: 172 passed.
- Main-agent rerun of functional API, Windows, and macOS tests: 149 passed at that review point.
- Cold-process imports did not load `accessibility_toolkit.runtime`.

### 3. `96124e5` - output and speech

Result: clean.

- Generic output, speech, settings, drivers, clipboard, and the vendored NVDA DLL moved to the specified functional ownership.
- `QueuedService` and speech behavior were preserved; import-only changes did not alter enum values, persisted engine IDs, settings schema, or wire models.
- `VENDORED_X64_DLL` is resolved relative to `nvda_controller.py`; the driver does not import runtime.
- `output` depends on `scheduling`, while no output module depends on `remote` or `runtime`.
- `output` and `output.speech` have explicit public APIs.

Non-blocking commit-scope observations:

- This commit also introduced the design/plan documents and changed older refactor documents.
- The macOS PyInstaller hidden-import migration was included here instead of the later packaging commit. The change itself is correct.

### 4. `710bc01` - interaction modes

Result: clean.

- `ModeManager` and `ActivationMode` moved into `interaction` with the specified explicit public API.
- Mode entry, exit, capture rollback, exit-key handling, and `ModeChanged` notification behavior were preserved.
- The dependency direction is exactly `interaction -> input, events`; app-specific modes remained under `apps/*`.

### 5. `d850a72` - remote package

Result in the current baseline: clean.

- Protocol messages, serializer, events, routing, session, and transport moved without wire-format or lifecycle changes.
- `remote.routing`, `remote.session`, and `remote.transport` expose explicit APIs.
- The only cross-feature dependency is the allowed `remote -> output.speech` wire-model edge.

Commit-local finding:

- The documented canonical import `from accessibility_toolkit.remote import RemoteSession` was not provided by this commit. A fix sub-agent confirmed that the later current baseline already imports and exports `RemoteSession` at the remote root, so no duplicate implementation was made. The current import, attribute, `__all__`, and no-runtime-load contracts all pass.

### 6. `cbaed7e` - hard cutover

Result: clean.

- The `application`, `application_support`, `interop`, and `adapters` package trees were fully deleted.
- No compatibility module or forwarding import remains.
- Runtime exposes the specified six composition symbols.
- Runtime test files were renamed and public API/removal contracts were added.
- The final tree contains only `input`, `output`, `scheduling`, `interaction`, `events`, `remote`, and `runtime` beneath the core package.

### 7. `60a38f3` - packaging

Result after fix/re-review: clean.

The package discovery, DLL package-data key, and PyInstaller paths were correct, but exact verification exposed a blocking defect not covered by the original static assertions:

```text
python -m build packages/accessibility-toolkit-core
...
error in 'egg_base' option: '../../src' does not exist or is not a directory
```

Root cause:

- Both distribution projects used `package-dir` and package discovery at `../../src`.
- Setuptools could build a wheel directly from the repository, but its sdist did not contain the external source tree or DLL.
- The extracted sdist therefore could not rebuild a wheel. The wx distribution had the same defect.

Fixes:

- Both projects now use a project-local `src` layout in their distribution metadata.
- A small in-tree PEP 517 backend stages only the distribution-owned package in a temporary project when building from the monorepo.
- Each sdist includes its backend and self-contained source tree, so it can rebuild independently without a symlink, permanent duplicate source tree, or new runtime dependency.
- Added round-trip tests for core and wx sdists, wheel isolation, and the NVDA DLL.

TDD and main-agent re-review evidence:

- RED: both packaging tests failed with the `../../src` `egg_base` error.
- GREEN: both packaging tests passed; reverting the TOML changes made both tests fail again.
- Exact main-agent builds of both projects succeeded and produced one sdist and one wheel each.
- Core wheel: 72 core package files, 0 wx files, 1 NVDA DLL.
- wx wheel: 9 wx package files, 0 core files.
- Core sdist contains the functional core sources, backend, and DLL; wx sdist contains only the wx source package and backend.
- Build staging left no `packages/*/src`, `build`, `dist`, or egg-info artifact in the working tree.

### 8. `d98ce6a` - current documentation

Result after fix/re-review: clean.

The new package trees and usage examples were present, but several dependency statements contradicted the design and implementation:

- They claimed that `input` currently consumes root `events`.
- They described `scheduling` as currently shared by input, output, and runtime, although `input -> scheduling` is explicitly future-only in this refactor.
- `InputActivationUseCase` was assigned to `interaction` instead of `input` in the current English and Traditional Chinese specs.

Fixes:

- Documented the actual edges: `output -> scheduling`, `interaction -> input, events`, `remote -> output.speech`, and `runtime -> all functional packages`.
- Clarified that `input -> scheduling` is allowed in the future but absent today.
- Corrected `InputActivationUseCase` ownership to `input`.
- Updated English and Traditional Chinese documents consistently.

Static dependency scans and source ownership checks match the corrected text.

## Review/fix rounds

### Round 1

The main agent reviewed all eight commits and found:

1. Missing public implementation exports in `input.windows` and `input.macos`.
2. Missing documented `WindowsKeyboardHook` API.
3. A commit-local missing `remote.RemoteSession` export, already resolved in the current baseline.
4. Incorrect current dependency and ownership documentation.
5. Core and wx sdists that could not independently rebuild wheels.

Each independent issue was assigned to a focused sub-agent. Production-code fixes used failing contract tests before implementation. Documentation fixes used spec/source comparison and static dependency verification.

### Round 2

The main agent reviewed every sub-agent diff rather than relying on its completion report. The first platform API fix still did not satisfy the exact `WindowsKeyboardHook` usage in the design, so it was sent back for a second TDD fix. The packaging solution was checked for optional tool dependencies, temporary artifact cleanup, distribution isolation, and round-trip behavior. No further blocking findings remained.

## Final verification

Fresh main-agent verification after all fixes:

```text
.venv/bin/python -m pytest tests/unit tests/integration -q
823 passed in 10.39s
```

Import verification succeeded for the core package, all seven functional packages, `WindowsKeyboardHook`, and `RemoteSession`.

Static boundary checks:

| Check | Result |
|---|---|
| Old technical-layer directories | Absent |
| Old namespace imports in `src` and `tests` | 0 matches |
| Removed adapter references in package/bundle metadata | 0 matches |
| `scheduling`/`events` importing feature packages | 0 matches |
| Feature packages importing `runtime` | 0 matches |
| Non-runtime feature packages importing `remote` | 0 matches |
| `remote -> output.speech` | Exactly 2 allowed wire-model imports |
| `git diff --check` | Clean |

Exact builds:

```text
.venv/bin/python -m build packages/accessibility-toolkit-core --outdir <tmp>/core
Successfully built accessibility_toolkit_core-0.1.0.tar.gz and accessibility_toolkit_core-0.1.0-py3-none-any.whl

.venv/bin/python -m build packages/accessibility-toolkit-wx --outdir <tmp>/wx
Successfully built accessibility_toolkit_wx-0.1.0.tar.gz and accessibility_toolkit_wx-0.1.0-py3-none-any.whl
```

The only build message is setuptools' non-blocking warning that each distribution project lacks its own README file. It does not affect source inclusion, wheel reconstruction, namespace isolation, or DLL inclusion.

Windows and macOS executable bundles were not built in this Linux review environment. Their spec files and hidden-import/resource paths were checked statically; platform import tests pass.

## Final verdict

**Approved after fixes.**

The reviewed implementation now satisfies the functional package structure, public API, dependency direction, hard-cut migration, documentation, package isolation, and vendored-resource requirements. The full test suite and both distribution round trips pass, and no Critical or Important review finding remains.
