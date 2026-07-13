# Legacy Payload Round-Trip Main Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lock the current HID-to-Windows legacy payload mappings with round-trip regression coverage without adding a runtime safe-set policy.

**Architecture:** Keep `legacy_payload_from_captured_event` as the existing two-mode bridge. Test the mapping contract at the payload adapter boundary by converting every supported HID usage to a legacy tuple and resolving it through the Windows HID map.

**Tech Stack:** Python, pytest, existing accessibility toolkit HID and Windows mapping modules.

## Global Constraints

- Do not add a runtime `ROUND_TRIP_SAFE_WINDOWS_HID_USAGES` set.
- Preserve `use_windows_native_key_payload` behavior.
- Preserve `num_lock_on` handling.

---

### Task 1: Add complete legacy payload round-trip coverage

**Files:**
- Modify: `tests/unit/test_nvda_remote_legacy_key_payload.py`
- Test: `tests/unit/test_nvda_remote_legacy_key_payload.py`

**Interfaces:**
- Consumes: `_USAGE_TO_LEGACY`, `key_event_to_legacy_remote_payload`, and `key_event_from_windows`.
- Produces: A regression test proving each supported mapping, including `HID.KEYPAD_EQUALS`, resolves back to its original usage.

- [ ] **Step 1: Add the regression test**

Add this test and import `key_event_from_windows`:

```python
def test_supported_legacy_payload_mappings_round_trip_through_windows_hid_map():
    for usage in _USAGE_TO_LEGACY:
        event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=usage, pressed=True)
        payload = key_event_to_legacy_remote_payload(event)

        remapped = key_event_from_windows(
            vk_code=payload["vk_code"],
            scan_code=payload["scan_code"],
            extended=payload["extended"],
            pressed=payload["pressed"],
        )

        assert remapped is not None
        assert remapped.usage == usage
```

The test intentionally reads the module's existing private mapping from the test module; this keeps the supported usage list single-sourced without adding a production API.

- [ ] **Step 2: Run the focused test to verify the current mapping**

Run:

```bash
PYTHONPATH=src pytest tests/unit/test_nvda_remote_legacy_key_payload.py::test_supported_legacy_payload_mappings_round_trip_through_windows_hid_map -q
```

Expected: PASS, including `KEYPAD_EQUALS` through scan code 89. This is a test-only regression task because the current production mapping already contains the required fix.

- [ ] **Step 3: Keep implementation minimal**

Do not add a safe set or change `src/apps/nvda_remote/legacy_key_payload_bridge.py`. The production mapping already uses:

```python
HID.KEYPAD_EQUALS: (187, 89, False)
```

and the bridge already passes `captured.num_lock_on` to the HID converter in default mode.

- [ ] **Step 4: Run focused regression coverage**

```bash
PYTHONPATH=src pytest tests/unit/test_nvda_remote_legacy_key_payload.py tests/unit/test_nvda_remote_legacy_key_payload_bridge.py -q
```

Expected: all tests pass with zero failures.

- [ ] **Step 5: Commit the regression coverage**

```bash
git add tests/unit/test_nvda_remote_legacy_key_payload.py
git commit -m "test: lock legacy payload hid round trips"
```

### Task 2: Run repository validation

**Files:**
- Test: `tests/unit/`
- Test: `tests/integration/`

**Interfaces:**
- Consumes: the completed round-trip regression and existing bridge behavior.
- Produces: verified unit and integration test results.

- [ ] **Step 1: Run the full test suite**

```bash
PYTHONPATH=src pytest tests/unit tests/integration -v
```

Expected: exit code 0 and zero failed tests.

- [ ] **Step 2: Inspect the final diff and status**

```bash
git diff --check
git status --short --branch
git show --stat --oneline HEAD
```

Expected: no whitespace errors; only the intended test and previously committed spec/plan changes are present.
