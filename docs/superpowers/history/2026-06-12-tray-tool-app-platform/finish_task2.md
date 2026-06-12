# Review Task 1 修正報告

## 審查來源

`docs/superpowers/review_task1.md`

## 審查結果確認

審查者指出一個 **High** 優先級問題，經確認正確：

### Issue: `nvda_remote.start_control()` 在未連線時留下半切換狀態

**問題**: 上一輪修正將 `enter_active()` 移入 `start_control()` 後，執行順序為：
1. `enter_active()` → 停止 `HotkeyCapture`、啟動 `InputCapture`、設 `control_state = CONTROLLING`
2. `control_mode.start_control()` → 檢查 `connection_state == IDLE` → "Not connected" 錯誤 → return

結果 call 失敗後仍留下 `control_state = CONTROLLING`、`InputCapture` 執行中、`HotkeyCapture` 已停止。這違反 spec 要求：失敗時不得留下半切換狀態。

**驗證**: `src/apps/nvda_remote/facade.py:135-138` — connection guard 在 `enter_active()` 之後。

## 修正內容

### `src/apps/nvda_remote/facade.py`

| 方法 | 修正前 | 修正後 |
|------|--------|--------|
| `start_control()` | `enter_active()` → `control_mode.start_control()`（connection check 在後者內部） | 先檢查 `connection_state == IDLE` 並 return，再 `enter_active()` → `control_mode.start_control()` |

### `src/apps/nvda_remote/use_cases/control_mode.py`

| 變更 | 說明 |
|------|------|
| `start_control()` 移除 connection guard | connection check 已移至 facade，避免 `enter_active()` 後才發現未連線 |
| 移除 `ConnectionState` import | 不再被參照 |

## 測試結果

```
PYTHONPATH=src python3 -m pytest tests/unit tests/integration -q
248 passed in 0.51s
```

## Commit

```
3bdaf84 fix: guard start_control against disconnected state before activation
```
