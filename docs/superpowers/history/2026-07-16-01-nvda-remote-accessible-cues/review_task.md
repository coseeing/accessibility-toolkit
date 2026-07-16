# NVDA Remote Accessible Cues Review

## Review scope

依 `docs/superpowers/finish_task.md` 列出的 10 個 commit，按 commit 時間由舊到新，對照：

- `docs/superpowers/specs/2026-07-16-nvda-remote-accessible-cues-design.md`
- `docs/superpowers/plans/2026-07-16-nvda-remote-accessible-cues.md`

審閱範圍只包含完成說明列出的 commit；既有 connection-manager 未提交修改保留不納入本次審閱。

## Commit-by-commit review

| 時間順序 | Commit | 審閱結果 |
| --- | --- | --- |
| 1 | `ac8076a fix: associate connection editor labels` | 通過。四個 mnemonic `StaticText` 與 Name/Host/Port/Key controls 成對排列，保留 accessible names、驗證、預設按鈕與 focus 行為。 |
| 2 | `f297dbc fix: preserve task report and assert label tuple` | 通過。補強 label tuple assertion 與交接紀錄。 |
| 3 | `830aef9 chore: keep handoff report untracked` | 通過。只移除不應納入版本控制的 handoff report。 |
| 4 | `68a2df9 feat: add asynchronous wave output` | 通過。Windows 使用 `winsound` async WAV，macOS 使用背景 `afplay`；unsupported platform、launch failure、playback failure 均 warning 且不向上拋出。 |
| 5 | `93ad0aa feat: expose wave output capability` | 通過。`WaveOutput` 沿 PlatformProvider → runtime parts → Capabilities 傳遞，並保留舊 provider fallback。 |
| 6 | `282ef56 fix: preserve capabilities positional order` | 通過。`Capabilities` 的既有 positional 欄位順序保持不變，wave 置於既有欄位之後。 |
| 7 | `cc99be4 feat: announce NVDA Remote state changes` | 發現問題：control mode 對重複 start/stop 仍會 callback、notify，造成重複語音。 connection lifecycle 的 CONNECTED/IDLE 去重與 CONNECTING→IDLE 不播報邏輯符合 spec。 |
| 8 | `5824fc8 build: package NVDA Remote cue sounds` | 通過。setuptools、Windows/macOS PyInstaller 均納入 waves、NOTICE 與 license。 |
| 9 | `9d0d4ff test: verify NVDA Remote wave wiring` | 通過。補上 runtime/app wiring 覆蓋。 |
| 10 | `99ffb4f fix: address broad review compatibility findings` | 通過既有相容性修正；但保留了上一項 control transition bug，已由後續 review iteration 修正。 |

## Review finding and correction loop

Root cause 位於 `NvdaRemoteControlModeUseCase.start_control()` 與
`stop_control()`：兩者原本無視目前 `ControlState`，每次呼叫都修改 state、觸發 cue callback 與 status event。

已委派 `gpt-5.6-terra medium` subagent 以 TDD 修正：

1. 先加入重複 start/stop 的 failing regression test，確認修正前會產生 `remote, remote, local, local`。
2. 加入 transition guards，只允許 `CONNECTED→CONTROLLING` 與 `CONTROLLING→CONNECTED` 發出 callback/notification。
3. 調整 `NvdaRemoteAppService` 的 input activation wiring，讓 use case 成為 control state transition 與 cue 的唯一來源，且 activation 失敗不會先播報成功 cue。
4. Terra focused validation：`48 passed`。
5. Main agent 重新檢查實際 diff、狀態流與相關呼叫路徑後，再執行完整驗證；未發現剩餘 spec 違反或 bug。

## Final validation

- `pytest tests/unit tests/integration -v`: **965 passed, 1 skipped**
- focused review suite: **88 passed**
- `git diff --check`: passed
- `connected.wav` 與 NVDA source byte-identical：passed
- `disconnected.wav` 與 NVDA source byte-identical：passed
- `NVDA-COPYING.txt` 與 `ref/nvda/copying.txt` byte-identical：passed
- Linux 未執行原生 Windows/macOS audio backend；平台行為由 mocked unit tests 覆蓋。

## Conclusion

本次 review 的唯一功能性問題已完成 Terra 修正並經 main agent 重審與完整測試確認；依指定 spec/plan，review 結果為通過。
