# WorldVoice pyttsx3 Small Migration Design

## 概述

本文件定義一個較小範圍的移植工作，用來優先滿足 `nvda-remote-client` 的語音輸出需求，而不立即啟動先前那份完整 `WorldVoice` host-agnostic core 重構方案。這次工作聚焦於兩件事：

- 在 `nvda-remote-client` 以比照 NVDA `_remoteClient.serializer` 的方式，於反序列化階段還原遠端 NVDA 機器送來的完整 speech sequence
- 從 `WorldVoice` 搬入 `taskManager` 的調度能力，並強化現有 `pyttsx3` backend，讓它可處理主要的 NVDA speech command

這次小移植的目標不是把 `WorldVoice` 全部搬進來，也不是先移植 `VE` driver。這一版只針對 `pyttsx3`、`taskManager`、speech command restoration，以及 GUI 中最小必要的語音控制介面進行定向修改。

## 目標

- 讓 `nvda-remote-client` 能還原遠端 NVDA speech sequence 為本地 command object sequence。
- 將 `WorldVoice` 的 `taskManager` 拷貝進 `nvda-remote-client` 並改寫成可在 client 宿主內使用。
- 強化現有 `pyttsx3` backend，讓它可吃完整 speech sequence，而不是只吃扁平化文字。
- 讓 `BreakCommand` 透過 `taskManager` 做真正停頓，而不是 no-op 或近似處理。
- 讓 `pyttsx3` backend 提供 `voice`、`rate`、`volume`、`pitch` 控制通道。
- 讓 `nvda-remote-client` GUI 提供最小控制介面，可選語音並調整速度、音量與音調。

## 不在這份設計內的範圍

- 不啟動完整 `WorldVoice` core 抽離。
- 不移植 `VE` driver。
- 不重構 `WorldVoice` repo 的既有 NVDA 相依 driver 邊界。
- 不支援所有 `WorldVoice` engines。
- 不把 NVDA settings ring、dialog、global plugin 搬進 `nvda-remote-client`。
- 不修改 NVDA Remote protocol。

## 背景與問題

目前 `nvda-remote-client` 的語音資料模型以 `NormalizedSpeech` 為主，只保留文字與 break 等簡化資訊。這樣的模型不足以保留遠端 NVDA speech sequence 中的 command object，例如：

- `BreakCommand`
- `PitchCommand`
- `RateCommand`
- `VolumeCommand`
- `IndexCommand`
- 其他 driver 可能自行處理的 `SpeechCommand`

另一方面，這次小移植不打算先引入 `VE`，而是先利用 repo 中已存在的 `pyttsx3` backend 做一條更容易落地的路徑。但如果 `pyttsx3` 仍只接受扁平化文字，則：

- `BreakCommand` 無法做真正停頓
- `taskManager` 的調度價值無法保留
- `rate`、`volume`、`pitch` command 的通道會被 client 層提前吃掉

所以正確的責任邊界應該是：

- `nvda-remote-client` 負責將遠端 speech sequence 還原成 object
- backend 負責判斷自己支援哪些 command，並自行執行
- `taskManager` 負責 break / speak / cancel 的排程與時序

## 核心設計決策

### 1. Client 還原 speech sequence，但不解讀 command

`nvda-remote-client` 必須完整還原遠端 NVDA speech sequence 中的 command object，但不在 client 層執行這些 command 的語意。這個還原動作應比照 NVDA `_remoteClient.serializer` 的作法，優先放在反序列化階段，而不是放在後續 router 或 backend 前處理階段。client 只負責重建 object sequence，然後把 sequence 原樣交給 backend。

### 2. Backend 保有 command interpretation 權限

這次移植後，`pyttsx3` backend 不再只吃單一文字字串，而是在 `speak(sequence)` 內自行處理：

- 文字
- `BreakCommand`
- `PitchCommand`
- `RateCommand`
- `VolumeCommand`
- 其他 `SpeechCommand`

client 不替 backend 做 command fallback、prosody 模擬或支援判斷。

### 3. `BreakCommand` 必須做真正停頓

這一點不是 best-effort。`BreakCommand` 必須透過移植過來的 `taskManager` 做真正停頓，因此 backend 應將 sequence 切成可排程片段，而不是只把所有文字串接後一次交給 `pyttsx3`。

### 4. 直接拷貝並修改 taskManager

這次不採 wrapper 優先，也不建立假的 NVDA runtime。做法是直接把 `WorldVoice` 的 `taskManager` 拷貝進 `nvda-remote-client`，再針對宿主差異做修改。

### 5. GUI 需提供最小可操作控制

這次不只要讓語音能說出來，也必須讓使用者可在 GUI 中：

- 選語音
- 調整速度
- 調整音量
- 調整音調

這些控制項應直接驅動 active backend，而不是在 client 層自行模擬。

### 6. `pitch` 以 best-effort 套用

`pyttsx3` 對 `pitch` 的支援會受底層系統 TTS engine 影響，因此這次應保證：

- UI 有 pitch 控制
- backend 有 pitch setter/getter
- backend 會嘗試套用

但不保證所有環境都能有完全一致的實際音高效果。失敗時應保持穩定，不可讓 client 崩潰。

## 建議架構

### `remote_core` / serializer 層

職責調整為：

- 在 JSON 反序列化時直接重建 `speak` 訊息中的 speech command object
- 比照 NVDA `_remoteClient.serializer.asSequence` 的模式，只在 `type == "speak"` 且有 `sequence` 時進行還原
- 不先把 speech 扁平化成簡化模型

### `remote_core` / routing 層

職責調整為：

- 接收已完成 command object 還原的 speech payload
- 直接轉交完整 speech sequence
- 不負責還原 speech command

### `application` 層

職責：

- 接收完整 speech sequence
- 將 sequence 交給 active speech backend
- 將 UI 變更傳給 backend 的 voice / rate / volume / pitch 控制 API

### `adapters.outputs`

新增或重構 speech backend 介面，讓 backend 能吃完整 speech sequence，而不只吃 `NormalizedSpeech`。

### `adapters.worldvoice_task`

新增從 `WorldVoice` 移植過來的 `taskManager` 模組。

職責：

- speak task scheduling
- break scheduling
- cancel
- completion / callback forwarding

### `adapters.windows.pyttsx3_output`

保留既有檔案位置，但擴充成 sequence-aware backend。

職責：

- 接收完整 speech sequence
- 在 backend 中逐項處理 command
- 使用移植過來的 `taskManager` 做 speak / break / cancel / completion 調度
- 管理 voice / rate / volume / pitch

## 主要元件

### `NVDA speech command compatibility layer`

在 `nvda-remote-client` 中新增一組 command 類別，作為本地相容層。至少需包含：

- `SpeechCommand`
- `IndexCommand`
- `CharacterModeCommand`
- `LangChangeCommand`
- `BreakCommand`
- `PitchCommand`
- `RateCommand`
- `VolumeCommand`

這些型別的目的不是完整重做 NVDA，而是讓 backend 可用 `isinstance()` 依原本設計處理 sequence。

### `SpeechSequence restoration`

新增反序列化 hook 邏輯，將遠端 speech payload 還原為：

- `list[str | SpeechCommand]`

這會成為新的 backend 主要輸入。作法應比照 NVDA `_remoteClient.serializer`：

- serialize 時把 command 轉成 `[class_name, instance_vars]`
- deserialize 時用 hook 檢查 `type == "speak"`
- 對 sequence 中的 list 項目，用 class name 找對應 command 類別
- 用 `__new__` 加 `__dict__.update(...)` 或等價方式重建物件

### `SpeechOutput` contract update

既有 `SpeechOutput.speak()` 只接受 `NormalizedSpeech`，這次應擴充或改寫成接受完整 speech sequence。

原則：

- backend 可選擇只支援其中一部分 command
- client 不負責先做 fallback
- sequence interpretation 留在 backend

### `TaskManager` transplant

直接拷貝 `WorldVoice` 的 `taskManager`，保留下列能力：

- queue worker
- `SpeechFuture`
- cancel token
- break task
- speech task timeout
- wait-done 行為

但移除或改寫：

- `getSynth()`
- `synthIndexReached`
- `synthDoneSpeaking`
- NVDA 專用通知轉送

改為使用 client 端 callback 或 backend-local 事件。

### `Enhanced pyttsx3 backend`

既有 `pyttsx3` backend 應升級成 sequence-aware backend。

這次的目標不是先優化程式風格，而是先讓下列路徑成立：

- import 成立
- backend 能建立
- `speak(sequence)` 能跑
- `taskManager` 能調度
- `BreakCommand` 會造成真正停頓
- voice / rate / volume / pitch 能被設定

## 資料流

建議資料流如下：

1. relay 收到遠端 speech payload
2. serializer 在 deserialize 階段將 payload 還原成 NVDA-style speech sequence object list
3. `OutputManager` 將 sequence 交給目前 active backend
4. `pyttsx3` backend 在 `speak(sequence)` 內逐項處理文字與 command
5. backend 遇到：
   - 文字：排入 speak task
   - `BreakCommand`：排入 break task
   - `PitchCommand` / `RateCommand` / `VolumeCommand`：更新目前或後續 speak 使用的參數
6. `taskManager` 依序執行 speak / break / speak
7. GUI 變更 `voice/rate/pitch/volume` 時，直接更新 backend 狀態

這個流程的關鍵是：

- serializer 負責 restoration
- backend 負責 interpretation
- `taskManager` 負責 execution scheduling

## GUI 控制介面

這次小移植必須在 `nvda-remote-client` GUI 中加入最小必要控制。

### 必要控制項

- voice selector
- rate control
- volume control
- pitch control

### 行為原則

- 選到 `pyttsx3` backend 時，UI 讀取可用語音清單與目前參數。
- 使用者修改 voice / rate / volume / pitch 時，直接呼叫 backend setter。
- 後續 speech 自動使用最新參數。
- 若某 backend 已知完全不支援某項控制，該控制項可停用。
- `pitch` 即使為 best-effort，也應保留 UI 與 API 通道。

### 責任邊界

- `ui` 只負責顯示與收集輸入
- `application/controller` 只負責轉發到 backend
- backend 負責真正套用參數
- `taskManager` 不管理設定值

## 高風險相依與處理方式

### 必須先改掉的相依

- 舊的 `NormalizedSpeech` 主路徑
- `SpeechOutput` 僅接受扁平化文字模型的假設
- `taskManager` 中的 NVDA 通知轉送
- 將 speech command 還原責任錯放到 router 的作法

### 可以先保留但要限制影響範圍的相依

- `pyttsx3` 底層 engine 差異
- `voice` 列表與 voice property 名稱
- `pitch` 的實際支援程度

這些不確定性應限制在 `pyttsx3` backend 內，不擴散到 routing、controller、UI 的資料模型。

### 這一版先不要碰的相依

- `VE` driver
- 其他 `WorldVoice` engines
- NVDA settings ring / dialogs
- global plugin
- say-all / speech hook 類功能

## 建議實作順序

1. 建立 client 端 `speech command` 相容層
2. 改 serializer / output path，讓完整 sequence 在反序列化後可直接傳給 backend
3. 拷貝並改 `taskManager`
4. 擴充 `pyttsx3` backend 讓它能接受完整 sequence
5. 先打通 `BreakCommand` 的真實停頓路徑
6. 再補上 `rate`、`volume`、`pitch` command 與 setter/getter
7. 補上 voice selector 與 GUI 控制
8. 最後補 cancel / pause / completion 等執行細節

這個順序的目的，是先把資料模型和 backend contract 改對，再處理調度與停頓，最後才補互動控制與參數能力。

## 驗收標準

### 架構驗收

- `nvda-remote-client` 能在反序列化階段還原遠端 speech payload 為 NVDA-style speech sequence object list
- active backend 可直接接收完整 sequence，而不是被迫只吃 `NormalizedSpeech`
- client 不負責執行 prosody command 語意

### 行為驗收

- `pyttsx3` backend 能在 `speak()` 內逐項處理 sequence
- 至少支援：
  - text
  - `BreakCommand`
  - `PitchCommand`
  - `RateCommand`
  - `VolumeCommand`
- `taskManager` 能執行 speak / break / cancel 的基本調度
- `BreakCommand` 會造成真正停頓
- GUI 可選語音、調整速度、音量、音調
- GUI 控制能實際作用到 `pyttsx3` backend
- `voice`、`rate`、`volume` 在後續 speech 中可實際生效
- `pitch` 至少具備 UI、API 與 backend 通道，實際效果為 best-effort

### 範圍驗收

- 不需要同時支援其他 `WorldVoice` engines
- 不需要啟動完整 `WorldVoice` core 抽離
- 不需要移植 `VE`

## 測試策略

### 單元測試

- serializer hook 將 speech payload 還原為 command object sequence
- `taskManager` 的 speak / break / cancel / completion 行為
- `pyttsx3` backend 對主要 command 的處理
- `BreakCommand` 是否透過 task scheduling 產生真實停頓
- GUI 控制變更是否正確傳到 backend

### 整合測試

- 遠端送來含文字、break、pitch、rate、volume 的 speech payload
- client 還原後交由 `pyttsx3` backend 正常執行
- 調整 voice / rate / volume / pitch 後，後續 speech 確實使用新參數

### 手動驗證

- 使用 `pyttsx3` backend 播放遠端語音
- 驗證停頓、語速、音量可感知改變
- 驗證 GUI 選語音與參數控制可即時生效
- 驗證 pitch 在目前環境下至少不會造成錯誤，若底層支援則可感知改變

## 風險與注意事項

- 若在 serializer 之後又把 speech sequence 扁平化，`taskManager` 與 command 邊界的價值會被抵消。
- 若 `BreakCommand` 不經過調度而只是字串處理，這次需求就沒有達成。
- `pyttsx3` 的 `pitch` 支援可能受底層 driver 限制，因此應明確以 best-effort 實作。
- 若不在這一版加入最小控制介面，backend 雖可運作，但使用者無法實際控制 voice 與參數。
- `NormalizedSpeech` 在過渡期可能仍需保留給其他簡單 backend 或舊測試使用，但不應再作為這條 `pyttsx3` 路徑的主模型。

## 最終建議

本設計建議先把這次工作定義為一個小範圍、目的明確的移植：在 `nvda-remote-client` 端建立比照 NVDA `_remoteClient.serializer` 的 speech command 相容層與反序列化還原機制，拷貝並改寫 `WorldVoice` 的 `taskManager`，並強化現有 `pyttsx3` backend，使 client 可以在 deserialize 階段還原遠端 speech sequence，並把完整 sequence 交給 backend 處理。同時補上最小 GUI 控制介面，讓語音、速度、音量與音調能被實際操作。這樣可以在不啟動完整 core 抽離、也不引入 `VE` 的前提下，先把最有價值且最容易落地的語音能力移進 `nvda-remote-client`。
