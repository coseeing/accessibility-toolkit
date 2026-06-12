# Review Findings

No functional findings in the listed fix commits.

## Verified Fixes

- `review_task0.md` 的兩個原始問題已維持修正：
  - idle 狀態下的 `Enter` 可以啟動 echo
  - `Enter` / `Escape` 只在正確的 echo state 下觸發狀態切換
- `review_task1.md` 先前記錄的 shutdown 問題也已修正：
  - `KeyEchoAppFacade.shutdown()` 現在會在 speech shutdown 前停止仍在執行的 `input_service`
  - focused reproduction 確認 `service.shutdown()` 後 capture `running` 由 `True` 變成 `False`

## Verification

- Reviewed the listed commits from [docs/superpowers/finish_task1.md](/workspace/nvda-remote-client/docs/superpowers/finish_task1.md) in chronological order:
  - `1978b93 fix: guard key_echo hotkeys with state and start capture at init`
  - `2988f79 fix: stop input capture on key_echo shutdown`
- Cross-checked against:
  - [docs/superpowers/review_task0.md](/workspace/nvda-remote-client/docs/superpowers/review_task0.md)
  - [docs/superpowers/specs/2026-06-11-app-service-splitting-design.md](/workspace/nvda-remote-client/docs/superpowers/specs/2026-06-11-app-service-splitting-design.md)
- Ran targeted tests:
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_key_echo_app_service.py tests/unit/test_key_echo_use_cases.py tests/unit/test_app_wx.py -v`
  - Result: `50 passed`
- Ran full suite:
  - `PYTHONPATH=src python3 -m pytest tests/unit tests/integration -q`
  - Result: `240 passed`
- Ran focused behavior checks and confirmed:
  - before shutdown: capture running `True`
  - after shutdown: capture running `False`
  - idle `Enter`: starts echo and is suppressed
  - running `Escape`: stops echo and is suppressed
