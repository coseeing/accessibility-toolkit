# Task 6: Searchable connection manager dialog

## Scope

Implemented the searchable wxPython connection manager dialog and Task 6 UI test support.
Task 6 changes span these scoped files:

- `src/ui/nvda_remote/connection_manager_dialog.py`
- `tests/unit/test_app_wx.py`
- `tests/unit/test_nvda_remote_connection_ui.py`
- `.superpowers/sdd/task-6-report.md`

The shared fake-wx surface contains the report-list and context-menu behavior used
by the Task 6 tests.

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

## Review fix report

The review identified three Task 6 issues. The fixes are included in the follow-up
commit:

1. Context-menu bindings now use the real wxPython API shape:
   `item.GetId()` and `menu.Bind(wx.EVT_MENU, handler, id=item.GetId())`.
   The shared fake implements unique generated menu IDs, `GetId()`, item
   enabling, separators, destruction, and callback storage.
2. Context-menu items are enabled from the current selection: Connect, Edit,
   Copy Link, and Quick Connect require one selection; Delete requires at least
   one; Move Up/Down require one selected visible row with a valid adjacent
   target. Boundary no-op actions are disabled.
3. Focused UI tests now use the shared fake wx surface and invoke bound event
   handlers for context-menu and keyboard behavior. Coverage includes unique
   menu IDs and callbacks, selection guards, visible-only Ctrl+A, multi-selection
   Ctrl+C rejection, group filtering, accessible names/focus, default button,
   and Escape behavior.

## Review-fix test evidence

```text
pytest tests/unit/test_nvda_remote_connection_ui.py -v
18 passed in 0.24s

pytest tests/unit/test_app_wx.py -v
32 passed in 0.17s

pytest tests/unit tests/integration -v
940 passed, 1 skipped in 3.33s
```

Additional checks:

```text
python3 -m compileall -q src/ui/nvda_remote/connection_manager_dialog.py
git diff --check
```

Both completed without errors before the review-fix commit.

## Final review fix

The final review fix changed the tests to invoke the stored wx event handlers
instead of calling private action methods directly. The coverage now dispatches
Enter, Shift+Enter, Alt+Up, Alt+Down, F2, Delete, single-selection Ctrl+C, and
the context-menu event through the fake wx bindings. It also verifies context-menu
cleanup after destruction. The production dialog clears its transient menu
reference in a `finally` block after `Destroy()`.

Review-fix verification:

```text
pytest tests/unit/test_nvda_remote_connection_ui.py -v
18 passed in 0.24s

pytest tests/unit/test_app_wx.py -v
32 passed in 0.17s

pytest tests/unit tests/integration -v
940 passed, 1 skipped in 3.33s
```

These commands completed successfully before the final review-fix commit.

## Re-review fix evidence

The final re-review fix was verified after all test changes:

```text
pytest tests/unit/test_nvda_remote_connection_ui.py -v
19 passed in 0.14s

pytest tests/unit/test_app_wx.py -v
32 passed in 0.18s

pytest tests/unit tests/integration -v
941 passed, 1 skipped in 2.28s
```

The final focused tests dispatch Enter, Alt+Up, Alt+Down, F2, Delete, and
single-selection Ctrl+C via the stored `EVT_CHAR_HOOK` binding, and dispatch the
context-menu test via the stored `EVT_CONTEXT_MENU` binding. `git diff --check`
and `python3 -m compileall -q src/ui/nvda_remote/connection_manager_dialog.py`
also completed without errors.
