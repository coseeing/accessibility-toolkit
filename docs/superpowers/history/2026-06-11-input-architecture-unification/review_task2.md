# Review Findings

## Medium

1. `nvda_remote.stop_control()` 在 idle 狀態下仍會把 `control_state` 錯誤地改成 `CONNECTED`。這次修正只把未連線的 guard 加到 `start_control()`，但 `stop_control()` 仍然在 `InputActivationUseCase.exit_active()` 回傳 `True` 後，無條件呼叫 `NvdaRemoteControlModeUseCase.stop_control()`。由於 `exit_active()` 在 already-idle 時會直接回傳成功，直接呼叫公開 controller surface `stop_control()` 仍會把 `idle/idle` 變成 `idle/connected`。這不是一般 UI 路徑會碰到的情況，但它代表公開 API 仍可能產生不合法狀態，與這次修正想恢復的 controller-surface 一致性仍有缺口。  
   References: [facade.py](/workspace/nvda-remote-client/src/apps/nvda_remote/facade.py:140), [control_mode.py](/workspace/nvda-remote-client/src/apps/nvda_remote/use_cases/control_mode.py:25)

## Fixed

- `review_task1.md` 記錄的 High 問題已修正：
  - 未連線直接呼叫 `start_control()` 不再先進入 activation lifecycle
  - focused reproduction 確認 `before: idle/idle, input=False, hotkey=True`，呼叫後仍維持 `after: idle/idle, input=False, hotkey=True`

## Verification

- Reviewed the listed commit from `docs/superpowers/finish_task2.md` in chronological order:
  - `3bdaf84 fix: guard start_control against disconnected state before activation`
- Cross-checked against:
  - [review_task1.md](/workspace/nvda-remote-client/docs/superpowers/review_task1.md)
  - [2026-06-11-input-architecture-unification-design.md](/workspace/nvda-remote-client/docs/superpowers/specs/2026-06-11-input-architecture-unification-design.md)
  - [2026-06-11-input-architecture-unification-implementation.md](/workspace/nvda-remote-client/docs/superpowers/plans/2026-06-11-input-architecture-unification-implementation.md)
- Ran targeted tests:
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_nvda_remote_app_service.py tests/unit/test_app_wx.py -v`
  - Result: `44 passed`
- Ran full suite:
  - `PYTHONPATH=src python3 -m pytest tests/unit tests/integration -q`
  - Result: `248 passed`
- Ran focused reproductions and confirmed:
  - disconnected `start_control()` now leaves lifecycle untouched and only reports `"Not connected"`
  - direct idle-state `stop_control()` still mutates `control_state` from `IDLE` to `CONNECTED`
