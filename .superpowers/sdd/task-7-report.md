# Task 7: Main-frame saved-only workflow

## Scope

- Replaced manual Host/Port/Key entry in `src/ui/nvda_remote/main_frame.py` with Manage Connections, Quick Connect, and Disconnect actions.
- Updated `tests/unit/test_app_wx.py` to cover saved-only controls and connection-state enablement while retaining control, clipboard, status, and app-shell coverage.
- Removed the main-frame automatic insecure TLS retry.

## RED evidence

Command:

```text
pytest tests/unit/test_app_wx.py -k 'main_frame' -v
```

Result before implementation: 5 failed, 5 passed, 16 deselected. The failures were the expected missing saved-only controls and legacy manual fields still being present.

## GREEN evidence

Focused main-frame run:

```text
pytest tests/unit/test_app_wx.py -k 'main_frame' -v
10 passed, 16 deselected
```

Selected app-shell run:

```text
pytest tests/unit/test_app_wx.py -k 'main_frame or nvda_remote_app or nvda_remote_main' -v
17 passed, 9 deselected
```

Full suite:

```text
pytest tests/unit tests/integration -v
935 passed, 1 skipped
```

Additional check:

```text
git diff --check
```

Passed with no whitespace errors.

## Concerns

None identified for Task 7. Pre-existing unrelated worktree changes were left untouched and are not part of the Task 7 commit.
