# Remove Generate Key Button Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove the connection editor's Generate Key button and all code and tests dedicated to key generation.

**Architecture:** Keep `ConnectionEditorDialog`'s manual key field and standard OK/Cancel flow unchanged. Delete only the helper, handler, control construction, layout entry, and event binding that support generated keys.

**Tech Stack:** Python, wxPython-compatible UI code, pytest with the repository's fake wx test fixture.

## Global Constraints

- Keep platform-specific UI behavior inside the existing UI module.
- Preserve all manual connection validation and dialog result behavior.
- Do not modify unrelated connection-manager or group-manager behavior.

---

### Task 1: Update connection editor regression coverage

**Files:**
- Modify: `tests/unit/test_nvda_remote_connection_ui.py`

**Interfaces:**
- Consumes: `ConnectionEditorDialog` from `ui.nvda_remote.connection_editor`.
- Produces: A test that verifies the dialog no longer exposes a Generate Key button, while existing editor tests remain unchanged.

- [ ] **Step 1: Replace the obsolete helper test with a failing UI absence test**

Remove the `unittest.mock.patch` import and replace `test_generate_key_is_seven_decimal_digits` with:

```python
def test_editor_does_not_expose_generate_key_button(monkeypatch):
    editor_module, _group_module = load_editor_ui(monkeypatch)
    dialog = editor_module.ConnectionEditorDialog(None)

    assert not hasattr(dialog, "generate_button")
```

- [ ] **Step 2: Run the focused test to verify it fails for the expected reason**

Run:

```bash
pytest tests/unit/test_nvda_remote_connection_ui.py::test_editor_does_not_expose_generate_key_button -v
```

Expected: FAIL because the current dialog still creates `generate_button`.

### Task 2: Remove production key-generation code

**Files:**
- Modify: `src/ui/nvda_remote/connection_editor.py`

**Interfaces:**
- Consumes: Existing `SavedConnection` validation and dialog controls.
- Produces: A connection editor with only OK and Cancel action buttons and no generated-key API.

- [ ] **Step 1: Remove the obsolete import and helper**

Delete `import secrets` and the complete `generate_key()` function.

- [ ] **Step 2: Remove the Generate Key control and event path**

Keep the action row as:

```python
button_row = wx.BoxSizer(wx.HORIZONTAL)
self.ok_button = wx.Button(panel, wx.ID_OK, "&OK")
self.cancel_button = wx.Button(panel, wx.ID_CANCEL, "&Cancel")
for button in (self.ok_button, self.cancel_button):
    button_row.Add(button, 0, wx.ALL, 4)
sizer.Add(button_row, 0, wx.ALL, 4)
panel.SetSizer(sizer)

self.ok_button.Bind(wx.EVT_BUTTON, self._on_ok)
self.cancel_button.Bind(wx.EVT_BUTTON, self._on_cancel)
```

Delete `_on_generate_key()` entirely.

- [ ] **Step 3: Run the focused UI tests**

Run:

```bash
pytest tests/unit/test_nvda_remote_connection_ui.py -v
```

Expected: all tests in the file pass.

### Task 3: Verify the repository change

**Files:**
- Inspect: `src/ui/nvda_remote/connection_editor.py`
- Inspect: `tests/unit/test_nvda_remote_connection_ui.py`

- [ ] **Step 1: Confirm no Generate Key references remain in scoped files**

Run:

```bash
rg -n "generate_button|_on_generate_key|generate_key|Generate Key" src/ui/nvda_remote/connection_editor.py tests/unit/test_nvda_remote_connection_ui.py
```

Expected: no matches.

- [ ] **Step 2: Run the complete test suite**

Run:

```bash
pytest tests/unit tests/integration -v
```

Expected: exit code 0 with zero failures.

- [ ] **Step 3: Review the final diff**

Run:

```bash
git diff --check
git diff -- src/ui/nvda_remote/connection_editor.py tests/unit/test_nvda_remote_connection_ui.py
```

Expected: only the requested key-generation removal is present and there are no whitespace errors.
