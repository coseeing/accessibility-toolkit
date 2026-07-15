# Task 5: Connection editor and group manager dialogs

## Scope

Implemented only the Task 5 UI work:

- `src/ui/nvda_remote/connection_editor.py`
- `src/ui/nvda_remote/group_manager_dialog.py`
- `tests/unit/test_nvda_remote_connection_ui.py`
- Task 5 fake-wx extensions in `tests/unit/test_app_wx.py`

Later `connection_manager_dialog.py` and `main_frame.py` work was not implemented.

## TDD evidence

### RED

Command:

```text
pytest tests/unit/test_nvda_remote_connection_ui.py -k 'generate_key or editor or group_manager' -v
```

Result: 5 tests collected and 5 failed with `ModuleNotFoundError` for the missing
`ui.nvda_remote.connection_editor` and `ui.nvda_remote.group_manager_dialog`
modules.

### GREEN

After the minimal implementations, the same command completed with:

```text
5 passed in 0.06s
```

The dialogs now provide the requested seven-digit secure key generation,
validated/trimmed editor results, masked key input, TLS-validation opt-out,
default-group protection, group add/rename/delete controls, one-shot delete
confirmation, connection movement to `Default`, and change callbacks.

## Verification

```text
git diff --check
```

Result: passed with no whitespace errors.

```text
pytest tests/unit tests/integration -v
```

Result: `927 passed, 1 skipped in 2.42s`.

## Self-review

- Fake wx constants, events, controls, and module-cache entries match the brief.
- `ConnectionEditorDialog` consumes `SavedConnection.create` for domain validation.
- `GroupManagerDialog` calls only `ConnectionManager` group APIs.
- The non-removable `Default` group cannot be renamed or deleted.
- No later Task 5-excluded dialogs or main-frame integration were added.
- Existing unrelated working-tree changes were preserved.

## Concerns

None identified within the Task 5 scope. The dialogs intentionally do not provide
connection-manager list actions, which belong to the later task.
