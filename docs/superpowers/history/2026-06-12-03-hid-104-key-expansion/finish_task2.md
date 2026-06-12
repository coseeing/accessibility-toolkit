# HID 104-Key Expansion Review — Task 1 Fix Report

## Review Feedback from `docs/superpowers/review_task1.md`

### Finding 1 (Accepted & Fixed): Flaky KEYPAD_EQUALS test

**Finding:** The new `test_windows_keyboard_hook_emits_hid_for_keypad_equals` test passes `ctypes.addressof(FakeKbdLlHookStruct(...))` inline, which can fail in isolation due to garbage collection of the temporary struct (observed as `seen == []`).

**Verification:** Attempted to reproduce in the current environment — the test passed in 10 consecutive isolation runs. However, inline `ctypes.addressof` of a temporary is fragile across CPython versions and optimization levels; the pointer may dangle if the temporary is collected before the callback reads it.

**Fix:** Changed to use a named local variable (`key_data = FakeKbdLlHookStruct(...)`) before `ctypes.addressof(key_data)`, matching the stable pattern used throughout the rest of the file.

**Commit:** `9ef8f7b` — `fix: use named variable in keypad_equals test to prevent gc flakiness`

## Verification

```
pytest tests/unit tests/integration -q → 310 passed in 0.56s
```

## Commit List (This Round)

| Commit | Description |
|--------|-------------|
| `9ef8f7b` | `fix: use named variable in keypad_equals test to prevent gc flakiness` |

## All Commits (Entire Feature, Cumulative)

| Commit | Description |
|--------|-------------|
| `c4cd6db` | `feat: expand hid constants for 104-key coverage` |
| `e2ca947` | `feat: expand windows hid mappings for 104-key coverage` |
| `83f1944` | `feat: expand macos hid mappings for 104-key coverage` |
| `a8ffea3` | `feat: complete ansi hid relay mappings` |
| `12fd20f` | `test: lock unsupported iso relay suppression behavior` |
| `8befb43` | `fix: add missing windows keypad_equals mapping to hid normalization` |
| `9ef8f7b` | `fix: use named variable in keypad_equals test to prevent gc flakiness` |
