# NVDA Remote Accessible Connection Cues — 完成說明

## 完成內容

- 連線編輯器新增 `&Name:`, `&Host:`, `&Port:`, `&Key:` mnemonic labels，並保留原有可存取名稱、驗證、預設按鈕與 focus 行為。
- 新增可選、非同步且 failure-safe 的 `WaveOutput`，支援 Windows `winsound` 與 macOS `afplay`。
- 將 wave capability 接入 platform provider、runtime parts 與 output capabilities，同時保留既有 positional API 相容性與舊 provider fallback。
- NVDA Remote 在實際連線/斷線與 remote/local control transition 播放或朗讀指定 cue，重複 transition 不重複提示。
- 封裝 NVDA verbatim WAV、`NOTICE.md` 與 `NVDA-COPYING.txt`，並更新 setuptools 與 Windows/macOS PyInstaller 資源設定。
- 透過 subagent-driven implementation、逐 task Sol high review，以及 broad whole-branch review 完成；Task 3 的 positional API 問題與 broad review 的三項重要問題均已退回修正並重審核准。

## 驗證結果

- `pytest tests/unit tests/integration -v`: **964 passed, 1 skipped**
- focused fix suite: **90 passed**；`tests/unit/test_app_wx.py`: **26 passed**
- WAV 與 license byte identity：三個 `cmp` checks 全部成功。
- `git diff --check`（排除不可修改的 verbatim `src/apps/nvda_remote/waves/NVDA-COPYING.txt`）：成功。
- Linux 環境未執行原生 Windows/macOS audio backend；平台行為由 focused mocked tests 覆蓋。

## 本次新增 commits

- `ac8076a fix: associate connection editor labels`
- `f297dbc fix: preserve task report and assert label tuple`
- `830aef9 chore: keep handoff report untracked`
- `68a2df9 feat: add asynchronous wave output`
- `93ad0aa feat: expose wave output capability`
- `282ef56 fix: preserve capabilities positional order`
- `cc99be4 feat: announce NVDA Remote state changes`
- `5824fc8 build: package NVDA Remote cue sounds`
- `9d0d4ff test: verify NVDA Remote wave wiring`
- `99ffb4f fix: address broad review compatibility findings`

既有工作樹中的 connection-manager 相關未提交修改未納入上述 commits，並已保留。
