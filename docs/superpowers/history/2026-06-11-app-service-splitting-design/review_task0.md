# Review Findings

## High

1. `key_echo` 的 `Enter` 啟動 hotkey 在實際 runtime 中不可達，無法完成 spec 要求的「未 echo -> 進入 echo mode」流程。`build_runtime()` 只建立並 `bind()` `KeyboardInputService`，但初始並不啟動 capture，因此 `KeyEchoAppFacade.handle_key_event()` 不會在 idle 狀態收到任何 `Enter`。目前測試只直接呼叫 facade 方法，沒有覆蓋真實 runtime 的 idle 啟動路徑，所以這個問題會被整套測試漏掉。這違反 spec 中「`Enter` while not echoing -> enter echo mode」的要求。  
   References: [src/apps/key_echo/main.py:43](/workspace/nvda-remote-client/src/apps/key_echo/main.py:43), [src/apps/key_echo/main.py:44](/workspace/nvda-remote-client/src/apps/key_echo/main.py:44), [src/apps/key_echo/facade.py:99](/workspace/nvda-remote-client/src/apps/key_echo/facade.py:99)

## Medium

1. `key_echo` 的 state-transition hotkeys 沒有依目前狀態加 guard，導致 `Enter` / `Escape` 會被無條件吞掉。`handle_key_event()` 先做 hotkey mapping，再決定是否委派給 echo input；因此在 echo 已經啟動時，`Enter` 仍會走 `START_ECHO` 分支並回傳 `SUPPRESS`，鍵本身不會被朗讀。相對地，`Escape` 在未 echo 狀態若未來有可達的 capture 路徑，也會被無條件當成 stop hotkey。Spec 定義的是條件式轉換: `Enter` 僅在未 echo 時啟動，`Escape` 僅在 echo 時停止，現況行為不符。  
   References: [src/apps/key_echo/facade.py:99](/workspace/nvda-remote-client/src/apps/key_echo/facade.py:99), [src/apps/key_echo/facade.py:101](/workspace/nvda-remote-client/src/apps/key_echo/facade.py:101), [src/apps/key_echo/facade.py:104](/workspace/nvda-remote-client/src/apps/key_echo/facade.py:104)

## Verification

- Reviewed the listed commits from `docs/superpowers/finish.md` in chronological order: `0dfa933`, `a5a7f08`, `4ebf326`, `160b886`, `d001897`, `b3c9353`, `baae676`.
- Cross-checked behavior against:
  - [docs/superpowers/specs/2026-06-11-app-service-splitting-design.md](/workspace/nvda-remote-client/docs/superpowers/specs/2026-06-11-app-service-splitting-design.md)
  - [docs/superpowers/plans/2026-06-11-app-service-splitting-implementation.md](/workspace/nvda-remote-client/docs/superpowers/plans/2026-06-11-app-service-splitting-implementation.md)
- Ran full tests: `PYTHONPATH=src python3 -m pytest tests/unit tests/integration -v` -> `240 passed`.
- Ran a focused runtime reproduction for `key_echo` and confirmed:
  - initial `KeyboardInputService.running` is `False`
  - there is no always-on capture path for idle `Enter`
  - while echo is already running, `Enter` is still consumed as a hotkey instead of going through normal echo input behavior
