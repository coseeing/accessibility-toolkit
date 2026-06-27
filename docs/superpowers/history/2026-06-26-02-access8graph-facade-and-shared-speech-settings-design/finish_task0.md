# Access8Graph Facade, Shared Speech Settings, and Output Manager Retirement — Completion Report

## Summary

All four milestones defined in `docs/superpowers/specs/2026-06-26-access8graph-facade-and-shared-speech-settings-design.md` have been implemented across 8 tasks. The plan defined in `docs/superpowers/plans/2026-06-26-access8graph-facade-and-shared-speech-settings-implementation.md` was executed using Subagent-Driven Development with per-task spec/code review gates.

## Commit List

| # | SHA | Subject | Milestone |
|---|-----|---------|-----------|
| 1 | `7ba9f85` | refactor: add access8graph navigation use cases | M1 |
| 2 | `220a8d0` | refactor: move access8graph flow lifecycle out of app service | M1 |
| 3 | `e267ff7` | refactor: extract access8graph command dispatch boundary | M2 |
| 4 | `41f67cf` | refactor: introduce shared speech settings facade | M3 |
| 5 | `fa01c4b` | refactor: pass speech settings facade separately to ui | M3 |
| 6 | `2c9837d` | refactor: move speech settings out of app services | M3 |
| 7 | `1d571a7` | refactor: move clipboard protocol out of output manager | M4 |
| 8 | `f4d6838` | refactor: remove output manager | M4 |

## Milestone Results

### M1: Access8Graph Flow Lifecycle and Facade Narrowing
- **New files:** `src/apps/access8graph/use_cases/__init__.py`, `graph_selection.py`, `navigation.py`
- **New tests:** `tests/unit/test_access8graph_use_cases.py` (9 tests)
- `Access8GraphNavigationMode` no longer calls private service methods (`_start_flow`, `_stop_flow`)
- Flow creation/teardown moved to `Access8GraphNavigationSession` and `MrtFlowFactory`
- Graph validation extracted to `GraphSelectionUseCase`

### M2: Independent Access8Graph Command Translation Boundary
- **New file:** `src/apps/access8graph/use_cases/command_dispatch.py`
- Translator instantiation moved from `handle_key_event()` to app service init
- `Access8GraphCommandDispatcher` separates translation vs dispatch vs mode semantics
- 3 new tests cover unknown keys, no active flow, and active flow command dispatch

### M3: Extract Shared Speech Settings into an Independent Facade
- **New file:** `src/apps/shared/speech_settings_facade.py`
- `SpeechSettingsFacade` provides independent API for speech engine/voice/numeric settings
- `SpeechSettingsController` now subclasses the facade for migration compatibility
- `ToolAppShell` accepts separate `speech_controller` parameter
- All three UI apps (`Access8GraphApp`, `NvdaRemoteApp`, `EchoApp`) pass `speech_controller` separately
- All three entrypoints (`main.py`) build `SpeechSettingsFacade` with combined callbacks
- 14 pass-through methods removed from all three app services (net -211 lines, +61 lines)
- `SpeechEngineChanged` status notifications preserved via `notify_speech_engine_changed` public method

### M4: Remove `application.output.Manager`
- **Deleted:** `src/application/output/manager.py`, `tests/unit/test_output_manager.py`
- **New file:** `src/application/output/clipboard.py` (ClipboardService protocol)
- `Manager` export removed from `application/output.__init__.py`
- `test_message_router.py` tests use explicit callback fakes instead of Manager
- `test_speech_backends.py` tests use direct output calls instead of Manager
- Zero remaining `_start_flow`, `_stop_flow`, or `application.output.Manager` references in production code

## Verification

- **Full test suite:** 603/603 passing (0 regressions)
- **Access8Graph tests:** 62/62 passing
- **Speech settings & UI tests:** 44/44 passing
- **Output & routing tests:** 75/75 passing
- **Architecture cleanup grep:** No `_start_flow`, `_stop_flow`, `application.output.manager`, or `Manager` in production code
- **Speech methods grep:** All speech settings methods exist only on `SpeechSettingsFacade`, not on any app service

## Net Effect

- `Access8GraphAppService` reduced from 270 lines to ~195 lines (private state and methods removed)
- Speech settings decoupled from all three app services into independent shared facade
- `application.output.Manager` fully retired (63 production lines removed + 113 test lines)
- Four new use-case modules with clear single responsibilities
- All user-visible behavior (keyboard handling, speech feedback, navigation start/stop, hotkey startup) preserved
