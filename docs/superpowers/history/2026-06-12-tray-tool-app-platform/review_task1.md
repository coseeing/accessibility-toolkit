# Review Findings

## High

1. `nvda_remote.start_control()` 現在會先執行 `InputActivationUseCase.enter_active()`，再進入 `NvdaRemoteControlModeUseCase.start_control()` 的連線 guard。這讓公開 controller surface 在「未連線卻直接呼叫 `start_control()`」時會先停掉 `HotkeyCapture`、啟動 `InputCapture`，並把 state 設成 `CONTROLLING`，之後才收到 `"Not connected"` 錯誤。結果是 call 失敗後仍留下 active capture 與錯誤的 `control_state`，違反 spec 對 `InputActivationUseCase` 的要求：只有在切換真的成功後才標記 active，且失敗時不能留下半切換狀態。focused reproduction 已確認 `before: idle/idle, input=False, hotkey=True`，呼叫後變成 `after: idle/controlling, input=True, hotkey=False`。  
   References: [facade.py](/workspace/nvda-remote-client/src/apps/nvda_remote/facade.py:135), [control_mode.py](/workspace/nvda-remote-client/src/apps/nvda_remote/use_cases/control_mode.py:18), [2026-06-11-input-architecture-unification-design.md](/workspace/nvda-remote-client/docs/superpowers/specs/2026-06-11-input-architecture-unification-design.md:109)

## Fixed

- `review_task0.md` 的兩個原始問題已修正：
  - `key_echo` 的 UI `Start` / `Stop` 現在會經過 activation lifecycle
  - `nvda_remote` 的 UI `Start Control` / `Stop Control` 現在也會經過 activation lifecycle

## Verification

- Reviewed the listed commit from `docs/superpowers/finish_task1.md` in chronological order:
  - `1f47ceb fix: restore UI-controller capture lifecycle consistency`
- Cross-checked against:
  - [review_task0.md](/workspace/nvda-remote-client/docs/superpowers/review_task0.md)
  - [2026-06-11-input-architecture-unification-design.md](/workspace/nvda-remote-client/docs/superpowers/specs/2026-06-11-input-architecture-unification-design.md)
  - [2026-06-11-input-architecture-unification-implementation.md](/workspace/nvda-remote-client/docs/superpowers/plans/2026-06-11-input-architecture-unification-implementation.md)
- Ran targeted tests:
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_nvda_remote_app_service.py tests/unit/test_key_echo_app_service.py tests/unit/test_app_wx.py -v`
  - Result: `59 passed`
- Ran full suite:
  - `PYTHONPATH=src python3 -m pytest tests/unit tests/integration -q`
  - Result: `248 passed`
- Ran focused reproductions and confirmed:
  - `key_echo` UI `start_echo()` now transitions to keyboard-active mode correctly
  - `key_echo` UI `stop_echo()` now restores idle hotkey mode correctly
  - `nvda_remote` UI `start_control()` / `stop_control()` now align with capture lifecycle while connected
  - `nvda_remote.start_control()` while disconnected still leaves the service in a false active state
