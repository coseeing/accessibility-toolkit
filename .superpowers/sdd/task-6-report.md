# Task 6: Searchable connection manager dialog

## Scope

Implemented the searchable wxPython connection manager dialog and Task 6 UI test support.
Only these Task 6 files were changed by this work:

- `src/ui/nvda_remote/connection_manager_dialog.py`
- `tests/unit/test_nvda_remote_connection_ui.py`

The requested fake-wx extensions are local to the Task 6 UI test helper, preserving
the prior shared fake-wx test file.

## RED evidence

After adding the six Task 6 behavior tests, before creating the production dialog:

```text
pytest tests/unit/test_nvda_remote_connection_ui.py -v
6 failed, 8 passed
```

Each new manager test failed with:

```text
ModuleNotFoundError: No module named 'ui.nvda_remote.connection_manager_dialog'
```

This confirmed the tests exercised behavior absent from the repository rather than
passing against existing code.

## GREEN evidence

After implementing the dialog and completing the local fake-wx surface:

```text
pytest tests/unit/test_nvda_remote_connection_ui.py -v
14 passed in 0.11s
```

Full required verification:

```text
pytest tests/unit tests/integration -v
936 passed, 1 skipped in 2.46s
```

Additional verification:

```text
python3 -m compileall -q src/ui/nvda_remote/connection_manager_dialog.py
git diff --check
```

Both completed without errors.

## Implemented behavior

- Case-insensitive search over connection name and host.
- Group selection and active-group persistence.
- Selection-preserving list refresh.
- New, edit, delete, group management, quick-connect, and copy-link actions.
- Confirmed single/multi-delete with quick-connect cleanup delegated to the manager.
- Connect dispatch with error reporting and persisted close-after-connect behavior.
- Filter-aware adjacent reordering.
- Enter, F2, Delete, Ctrl+A, Ctrl+C, and Alt+Up/Down keyboard mappings.
- Context menu actions for connect, edit, copy, quick connect, movement, and delete.
- No reversed-connect or startup-auto-connect actions.

## Concerns

- The real wxPython runtime was not available in this Linux test environment; UI
  behavior was verified through the repository's fake-wx tests.
- Existing unrelated worktree changes were preserved and excluded from the Task 6
  commit.
