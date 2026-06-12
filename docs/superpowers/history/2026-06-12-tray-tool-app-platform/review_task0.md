# Review Findings

## High

1. `key_echo` 的公開 controller surface 已失去與 input lifecycle 的一致性，UI 的 `Start` / `Stop` 按鈕不再真正切換 capture 擁有權。`KeyEchoAppFacade.start_echo()` / `stop_echo()` 只改 `KeyEchoControlUseCase` 的狀態，完全不呼叫 `InputActivationUseCase.enter_active()` / `exit_active()`。因此 UI 點擊 `Start` 時，只會把 `is_echo_running()` 設成 `True`，但 `InputCapture` 仍是停止狀態、`HotkeyCapture` 仍保持執行；反過來，若先用 `Enter` 進入 active，再點 UI 的 `Stop`，也只會把 echo state 清掉，`InputCapture` 仍持續執行、`HotkeyCapture` 也不會恢復。這直接違反 spec 對「保留目前 UI-facing controller behavior」與 `idle hotkey / active keyboard` lifecycle 的要求。  
   References: [facade.py](/workspace/nvda-remote-client/src/apps/key_echo/facade.py:67), [facade.py](/workspace/nvda-remote-client/src/apps/key_echo/facade.py:72), [main_frame.py](/workspace/nvda-remote-client/src/ui/echo/main_frame.py:36), [2026-06-11-input-architecture-unification-design.md](/workspace/nvda-remote-client/docs/superpowers/specs/2026-06-11-input-architecture-unification-design.md:20)

2. `nvda_remote` 有相同的 controller-surface 回歸：公開的 `start_control()` / `stop_control()` 已不再驅動 capture lifecycle。重構後只有 idle `F11` 會經過 `_handle_idle_hotkey()` 進入 `InputActivationUseCase.enter_active()`，但 UI 按鈕仍直接呼叫 `start_control()` / `stop_control()`。結果是 UI 點 `Start Control` 時，只會把 `control_state` 改成 `CONTROLLING`，但 `InputCapture` 沒有啟動、`HotkeyCapture` 也沒有停掉；若先用 `F11` 進入 active，再點 UI 的 `Stop Control`，則只會改回 `CONNECTED`，`InputCapture` 仍繼續執行且 `HotkeyCapture` 不會恢復。這同樣破壞了 spec 要求的既有 UI 行為相容性。  
   References: [facade.py](/workspace/nvda-remote-client/src/apps/nvda_remote/facade.py:110), [facade.py](/workspace/nvda-remote-client/src/apps/nvda_remote/facade.py:137), [facade.py](/workspace/nvda-remote-client/src/apps/nvda_remote/facade.py:140), [main_frame.py](/workspace/nvda-remote-client/src/ui/nvda_remote/main_frame.py:79), [2026-06-11-input-architecture-unification-design.md](/workspace/nvda-remote-client/docs/superpowers/specs/2026-06-11-input-architecture-unification-design.md:20)

## Verification

- Reviewed the listed commits from `docs/superpowers/finish_task0.md` in chronological order:
  - `76cff16`
  - `6b5feec`
  - `797c165`
  - `5552dc4`
  - `4e9b338`
  - `93edac4`
  - `4260c4b`
  - `d4bddff`
  - `ee8a783`
  - `9c8cb9d`
  - `b22ea8f`
- Cross-checked behavior against:
  - [2026-06-11-input-architecture-unification-design.md](/workspace/nvda-remote-client/docs/superpowers/specs/2026-06-11-input-architecture-unification-design.md)
  - [2026-06-11-input-architecture-unification-implementation.md](/workspace/nvda-remote-client/docs/superpowers/plans/2026-06-11-input-architecture-unification-implementation.md)
- Ran full test suite:
  - `PYTHONPATH=src python3 -m pytest tests/unit tests/integration -v`
  - Result: `248 passed`
- Ran focused reproductions and confirmed:
  - `key_echo` UI-style `start_echo()` leaves `InputCapture` stopped and `HotkeyCapture` running
  - `key_echo` hotkey-entered active state followed by UI-style `stop_echo()` leaves `InputCapture` running
  - `nvda_remote` UI-style `start_control()` leaves `InputCapture` stopped and `HotkeyCapture` running
  - `nvda_remote` hotkey-entered active state followed by UI-style `stop_control()` leaves `InputCapture` running

## Testing Gap

- The current wx tests still pass because they exercise `FakeController` / `FakeEchoController` surfaces rather than the real app facades wired through the runtime. That leaves the UI-controller compatibility contract unverified for the actual implementations.
