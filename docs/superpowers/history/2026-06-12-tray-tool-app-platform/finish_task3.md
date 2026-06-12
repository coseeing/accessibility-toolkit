# Review Task 2 修正報告

## 審查來源

`docs/superpowers/review_task2.md`

## 審查結果確認

審查者指出一個 **Medium** 優先級問題，經確認正確：

### Issue: `nvda_remote.stop_control()` 在 idle 狀態下仍會錯誤地把 `control_state` 改成 `CONNECTED`

**問題**: `stop_control()` 無條件呼叫 `exit_active()`，而 `exit_active()` 在 `is_active()` 為 False 時會直接回傳 True（guard: `if not self._is_active(): return True`）。之後再呼叫 `control_mode.stop_control()` 將 `control_state` 從 `IDLE` 設為 `CONNECTED`。結果是從合法狀態 `idle/idle` 變成非法狀態 `idle/connected`。

**驗證**: `src/apps/nvda_remote/facade.py:143-148` — `stop_control()` 的 `exit_active()` 呼叫後無條件執行 `control_mode.stop_control()`（`_is_active` guard 未覆蓋到非 controlling 狀態）。

## 修正內容

### `src/apps/nvda_remote/facade.py`

| 方法 | 修正前 | 修正後 |
|------|--------|--------|
| `stop_control()` | `exit_active()` → `control_mode.stop_control()` | 先檢查 `control_state != CONTROLLING` 並 return，再 `exit_active()` → `control_mode.stop_control()` |

修正後的 `stop_control()` 只在真正 controlling 時才執行，非 controlling 狀態直接 return（idle 或 connected 狀態下 stop_control 本應為 no-op）。

## 與前次修正的一致性

| 方法 | Guard | 說明 |
|------|-------|------|
| `start_control()` | `connection_state == IDLE` → return | 上次修正：未連線不進入 activation |
| `start_control()` | `enter_active()` guard → return | 已 active 時 no-op |
| `stop_control()` | `control_state != CONTROLLING` → return | 本次修正：非 controlling 時 no-op |
| `stop_control()` | `exit_active()` guard → return | 已 idle 時 no-op |

## 測試結果

```
PYTHONPATH=src python3 -m pytest tests/unit tests/integration -q
248 passed in 0.43s
```

## Commit

```
3ae0839 fix: guard stop_control to prevent state mutation when not controlling
```
