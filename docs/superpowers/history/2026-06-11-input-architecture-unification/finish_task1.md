# Review Task 0 修正報告

## 審查來源

`docs/superpowers/review_task0.md`

## 審查結果確認

審查者指出兩個 **High** 優先級問題，經確認均為正確：

### Issue 1: key_echo 的公開 controller surface 與 input lifecycle 不一致

**問題**: `KeyEchoAppFacade.start_echo()` / `stop_echo()` 只改變 `KeyEchoControlUseCase` 的內部狀態，完全不呼叫 `InputActivationUseCase.enter_active()` / `exit_active()`。UI 按鈕點擊時，capture 擁有權不會切換：
- UI `Start` → `is_echo_running()` = True，但 `InputCapture` 仍停止、`HotkeyCapture` 仍執行
- 先用 `Enter` 熱鍵進入 active，再點 UI `Stop` → echo flag 清除，但 `InputCapture` 仍執行、`HotkeyCapture` 未恢復

**驗證**: `src/apps/key_echo/facade.py:67-70` — `start_echo()` 僅呼叫 `self._echo_control.start_echo()`，未觸及 `_activation`。  
UI 呼叫路徑: `src/ui/echo/main_frame.py:40` → `controller.start_echo()`

### Issue 2: nvda_remote 的公開 controller surface 與 input lifecycle 不一致

**問題**: `NvdaRemoteAppFacade.start_control()` / `stop_control()` 只改變 `control_state`，完全不呼叫 `InputActivationUseCase.enter_active()` / `exit_active()`。UI 按鈕點擊時，capture 擁有權不會切換：
- UI `Start Control` → `control_state` = CONTROLLING，但 `InputCapture` 未啟動、`HotkeyCapture` 未停止
- 先用 `F11` 熱鍵進入 active，再點 UI `Stop Control` → `control_state` = CONNECTED，但 `InputCapture` 仍執行、`HotkeyCapture` 未恢復

**驗證**: `src/apps/nvda_remote/facade.py:137-138` — `start_control()` 僅呼叫 `self._control_mode.start_control()`，未觸及 `_activation`。  
UI 呼叫路徑: `src/ui/nvda_remote/main_frame.py:83` → `controller.start_control()`

## 修正內容

### `src/apps/key_echo/facade.py`

| 方法 | 修正前 | 修正後 |
|------|--------|--------|
| `start_echo()` | 只呼叫 `_echo_control.start_echo()` | 先呼叫 `_activation.enter_active()`，失敗則 return，再呼叫 `_echo_control.start_echo()` |
| `stop_echo()` | 只呼叫 `_echo_control.stop_echo()` | 先呼叫 `_activation.exit_active()`，再呼叫 `_echo_control.stop_echo()` |
| `_handle_idle_hotkey()` | 自管 `enter_active()` + `start_echo()` | 簡化為只呼叫 `self.start_echo()`（capture 由 `start_echo()` 管理） |
| `_exit_active_from_keyboard()` | 自管 `exit_active()` + `stop_echo()` | 簡化為只呼叫 `self.stop_echo()`（capture 由 `stop_echo()` 管理） |

### `src/apps/nvda_remote/facade.py`

| 方法 | 修正前 | 修正後 |
|------|--------|--------|
| `start_control()` | 只呼叫 `_control_mode.start_control()` | 先呼叫 `_activation.enter_active()`，失敗則 return，再呼叫 `_control_mode.start_control()` |
| `stop_control()` | 只呼叫 `_control_mode.stop_control()` | 先呼叫 `_activation.exit_active()`，失敗則 return，再呼叫 `_control_mode.stop_control()` |
| `_handle_idle_hotkey()` | 自管 `enter_active()` + dispatch `start_control` | 簡化為只 dispatch `self.start_control`（capture 由 `start_control()` 管理） |
| `_exit_active_from_keyboard()` | 自管 `exit_active()` + 條件式 `stop_control()` | 簡化為只呼叫 `self.stop_control()`（capture 由 `stop_control()` 管理） |

## 安全考量

所有 `enter_active()` / `exit_active()` 呼叫均受 `InputActivationUseCase` 內部的 `_is_active()` guard 保護，不會重複進入/退出。熱鍵路徑與 UI 路徑可安全共存：
- 熱鍵進入 active → `_handle_idle_hotkey()` → `start_control()` → `enter_active()` (guard: no-op if already active)
- UI 進入 active → `start_control()` → `enter_active()` (same guard)
- 同理適用於退出路徑

## 測試結果

```
PYTHONPATH=src python3 -m pytest tests/unit tests/integration -v
248 passed in 0.56s
```

## Commit

```
1f47ceb fix: restore UI-controller capture lifecycle consistency
```
