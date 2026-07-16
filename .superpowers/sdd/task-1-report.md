# Task 1 Report: Associate Visible Connection Editor Labels

## Status

Implemented the visible mnemonic label associations for the connection editor.

## Implementation

- Retained the editor panel as `ConnectionEditorDialog.panel`.
- Added `ConnectionEditorDialog.field_labels` as a tuple of `(StaticText, control)` pairs in visual/focus order.
- Added the mnemonic labels `&Name:`, `&Host:`, `&Port:`, and `&Key:`.
- Kept the existing stable `SetName` calls, validation behavior, default button, escape behavior, and initial focus.
- Added a regression test that verifies label text, control identity, row ordering, and native sibling ordering.

## Files changed

- `src/ui/nvda_remote/connection_editor.py`
- `tests/unit/test_nvda_remote_connection_ui.py`

The pre-existing unrelated changes in `connection_editor.py` and `tests/unit/test_app_wx.py` were preserved. `tests/unit/test_app_wx.py` was not modified.

## Test execution

### RED

`pytest tests/unit/test_nvda_remote_connection_ui.py::test_editor_pairs_visible_mnemonic_labels_with_fields -v`

Result: failed as expected with `AttributeError: 'ConnectionEditorDialog' object has no attribute 'field_labels'`.

### GREEN

`pytest tests/unit/test_nvda_remote_connection_ui.py::test_editor_pairs_visible_mnemonic_labels_with_fields -v`

Result: `1 passed`.

`pytest tests/unit/test_nvda_remote_connection_ui.py -v`

Result: `20 passed`.

`pytest tests/unit tests/integration -v`

Result: `943 passed, 1 skipped`.

`git diff --check`

Result: passed with no whitespace errors.

## Self-review

The implementation is limited to the requested connection editor behavior. The new test exercises the public `field_labels` interface and the fake panel's actual sizer structure. No changes were made to `tests/unit/test_app_wx.py`.

## Commit

Committed as `fix: associate connection editor labels`.
