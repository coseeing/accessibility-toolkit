# Access8Graph GUI MRT Migration Review Fixes - Task 1

## Review Source

`docs/superpowers/review_task0.md` - identified 1 Critical, 1 High, and 1 Medium issue.

## Fixes Applied (commit `1bcd13d`)

### Critical: Invalid GraphML enters active navigation instead of failing before keyboard capture

**Root cause:** `Graph.load()` caught `BaseException`, printed it, and returned silently. `_start_flow()` set `_navigation_running = True` before parsing. `Access8GraphNavigationMode.enter()` always returned `True`, so `ModeManager` never triggered rollback via `exit_active()`.

**Fixes:**

| File | Change |
|------|--------|
| `src/apps/access8graph/graphml/model.py:308-312` | Changed `except BaseException: print(e); return` to `except Exception as e: raise ValueError(...) from e`. Parse failures now raise instead of being silently swallowed. |
| `src/apps/access8graph/service.py:134` | Removed redundant `self._navigation_running = True` from `_start_flow()`. The flag is already set by `InputActivationUseCase.enter_active()` AFTER successful capture start. |
| `src/apps/access8graph/service.py:35-41` | `Access8GraphNavigationMode.enter()` now wraps `_start_flow()` in try/except, notifies error via status listener, and returns `False` on failure. `ModeManager.activate_mode()` then calls `exit_active()` to roll back keyboard capture and restore hotkey capture. |

### High: Selected file validation incomplete

**Root cause:** `choose_graphml()` did case-sensitive suffix check and did not verify file existence.

**Fixes:**

| File | Change |
|------|--------|
| `src/apps/access8graph/service.py:109-114` | Suffix check now uses `.suffix.lower() == ".graphml"`. Added `.is_file()` existence check in `choose_graphml()`. |
| `src/apps/access8graph/service.py:117-124` | `start_navigation()` re-validates file existence before calling `activate_mode()`, protecting against deleted-after-selection. Raises `FileNotFoundError` if file no longer exists. Checks `activate_mode()` return value, raises `RuntimeError("Failed to start navigation")` on failure. |

### Medium: UI error status overwritten immediately by `_sync_controls()`

**Root cause:** `_on_controller_status()` called `_sync_controls()` unconditionally after setting error label, which overwrote the error text with "Navigation running" or file name.

**Fixes:**

| File | Change |
|------|--------|
| `src/ui/access8graph/main_frame.py:87-90` | Changed `_on_controller_status()` to `return` early after setting error label, skipping `_sync_controls()`. |

## Regression Tests Added (5 new tests)

| Test | What it verifies |
|------|------------------|
| `test_service_rejects_non_existent_file_in_choose_graphml` | `FileNotFoundError` on missing path |
| `test_service_accepts_uppercase_graphml_suffix` | `.GRAPHML` extension accepted |
| `test_service_malformed_graphml_does_not_leave_input_capture_running` | Invalid XML: `is_navigation_running()` is False, `input_capture.running` is False, `hotkey_capture.running` restored to True |
| `test_service_deleted_file_fails_before_activation` | File deleted after selection: `FileNotFoundError` raised, captures not activated |
| `test_main_frame_preserves_error_label_from_controller_status` | Error label persists after controller emits error status |

## Verification

```
pytest tests/unit tests/integration -v
425 passed in 0.68s
```

## Commit List (this review fix)

```
1bcd13d fix: harden graph loading validation, activation rollback and UI error persistence
```
