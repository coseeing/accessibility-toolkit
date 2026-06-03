# WorldVoice VE Small Migration Design

## 概述

本文件定義一個較小範圍的移植工作，用來優先滿足 `nvda-remote-client` 的語音輸出需求，而不立即啟動先前那份完整 `WorldVoice` host-agnostic core 重構方案。這次工作聚焦於從 `WorldVoice` 搬入 `taskManager` 與 `VE` 相關程式，讓 `nvda-remote-client` 可以還原遠端 NVDA 機器送來的 speech sequence，並把完整的 NVDA-style speech command object sequence 交由 driver 自行處理。

這次小移植的目標不是把 `WorldVoice` 全部搬進來，也不是把所有既有 driver 全部改成可跨宿主使用。這一版只針對 `VE` 與 `taskManager` 進行定向移植，同時在 `nvda-remote-client` GUI 中補上最小必要的 voice、rate、volume、pitch 控制介面。

## 目標

- 讓 `nvda-remote-client` 能還原遠端 NVDA speech sequence 為本地 command object sequence。
- 將 `WorldVoice` 的 `taskManager` 拷貝進 `nvda-remote-client` 並改寫成可在 client 宿主內使用。
- 將 `WorldVoice` 的 `VE` 相關程式拷貝進 `nvda-remote-client` 並做最小必要改寫。
- 讓 speech sequence 的解讀責任留在 driver，而不是由 client 先扁平化或預處理。
- 讓 `nvda-remote-client` 提供最小控制介面，可選語音並調整速度、音量與音調。

## 不在這份設計內的範圍

- 不啟動完整 `WorldVoice` core 抽離。
- 不重構 `WorldVoice` repo 的既有 NVDA 相依 driver 邊界。
- 不支援所有 `WorldVoice` engines。
- 不把 NVDA settings ring、dialog、global plugin 搬進 `nvda-remote-client`。
- 不修改 NVDA Remote protocol。

## 背景與問題

目前 `nvda-remote-client` 的語音資料模型以 `NormalizedSpeech` 為主，只保留文字與 break 等簡化資訊。這樣的模型不足以保留遠端 NVDA speech sequence 中的 command object，例如：

- `PitchCommand`
- `RateCommand`
- `VolumeCommand`
- `IndexCommand`
- 其他 driver 可能自行處理的 `SpeechCommand`

另一方面，`WorldVoice` 的 `VE` driver 本身已經在 `speak()` 內逐項走訪 speech sequence，並依 command 類型決定如何處理。這代表正確的責任邊界應該是：

- `nvda-remote-client` 負責將遠端 speech sequence 還原成 object
- backend / driver 負責判斷自己支援哪些 command，並自行執行

若 client 先把 speech 扁平化成文字與少數片段，`VE` driver 原本的 command 處理能力就會直接失效。

## 核心設計決策

### 1. Client 還原 speech sequence，但不解讀 command

`nvda-remote-client` 必須完整還原遠端 NVDA speech sequence 中的 command object，但不在 client 層執行這些 command 的語意。client 只負責重建 object sequence，然後把 sequence 原樣交給 backend。

### 2. Driver 保有 command interpretation 權限

這次移植後，`VE` backend 仍沿用 `WorldVoice` / NVDA driver 的模式，在 `speak(sequence)` 內自行處理：

- 文字
- `BreakCommand`
- `PitchCommand`
- `RateCommand`
- `VolumeCommand`
- 其他 `SpeechCommand`

也就是說，client 不會替 driver 做 command fallback、prosody 模擬或支援判斷。

### 3. 直接拷貝並修改 taskManager 與 VE 程式

這次不採 wrapper 優先，也不建立假的 NVDA runtime。做法是直接把 `WorldVoice` 的 `taskManager` 與 `VE` 相關程式拷貝進 `nvda-remote-client`，再針對宿主差異做修改。

### 4. WorldVoice 端既有 NVDA 相依 driver 保持原樣

這份小移植不處理 `WorldVoice` repo 內 driver 的全面重構。`WorldVoice` 端可以繼續使用目前那些依賴 NVDA 的既有 driver。若 `nvda-remote-client` 要使用對應能力，則在 client 端做定向改寫與移植。

### 5. GUI 需提供最小可操作控制

這次不只要讓語音能說出來，也必須讓使用者可在 GUI 中：

- 選語音
- 調整速度
- 調整音量
- 調整音調

這些控制項應直接驅動 active backend，而不是在 client 層自行模擬。

## 建議架構

### `remote_core` / routing 層

職責調整為：

- 接收遠端 speech payload
- 還原成 NVDA-style speech sequence object list
- 不先把 speech 扁平化成簡化模型

### `application` 層

職責：

- 接收完整 speech sequence
- 將 sequence 交給 active speech backend
- 將 UI 變更傳給 backend 的 voice / rate / volume / pitch 控制 API

### `adapters.outputs`

新增或重構 speech backend 介面，讓 backend 能吃完整 speech sequence，而不只吃 `NormalizedSpeech`。

### `adapters.worldvoice_ve`

新增一組從 `WorldVoice` 移植過來的 `VE` 相關模組。

職責：

- 接收完整 speech sequence
- 在 driver 中逐項處理 command
- 使用移植過來的 `taskManager` 做 speak / break / cancel / completion 調度

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

這些型別的目的不是完整重做 NVDA，而是讓移植過來的 driver 能用 `isinstance()` 依原本設計處理 sequence。

### `SpeechSequence restoration`

新增 payload 還原邏輯，將遠端 speech payload 還原為：

- `list[str | SpeechCommand]`

這會成為 `VE` backend 的主要輸入。

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

### `VE backend` transplant

直接拷貝 `WorldVoice` 的 `VE` 相關程式並修改。

這次的目標不是先優化程式風格，而是先讓下列路徑成立：

- import 成立
- backend 能建立
- `speak(sequence)` 能跑
- `taskManager` 能調度
- voice / rate / volume / pitch 能被設定

## 資料流

建議資料流如下：

1. relay 收到遠端 speech payload
2. router 將 payload 還原成 NVDA-style speech sequence object list
3. `OutputManager` 將 sequence 交給目前 active backend
4. `VE` backend 在 `speak(sequence)` 內逐項處理文字與 command
5. `taskManager` 負責 break / speak / cancel / completion 調度
6. backend 視需要回報 index / done / cancel 事件給 client

這個流程的關鍵是：

- client 負責 restoration
- driver 負責 interpretation
- `taskManager` 負責 execution scheduling

## GUI 控制介面

這次小移植必須在 `nvda-remote-client` GUI 中加入最小必要控制。

### 必要控制項

- voice selector
- rate control
- volume control
- pitch control

### 行為原則

- 選到 `VE` backend 時，UI 讀取可用語音清單與目前參數。
- 使用者修改 voice / rate / volume / pitch 時，直接呼叫 backend setter。
- 後續 speech 自動使用最新參數。
- 若某 backend 不支援某項控制，該控制項應停用，而不是由 client 自行模擬。

### 責任邊界

- `ui` 只負責顯示與收集輸入
- `application/controller` 只負責轉發到 backend
- backend 負責真正套用參數
- `taskManager` 不管理設定值

## 高風險相依與處理方式

### 必須先改掉的相依

- `synthDriverHandler` 相關依賴
- `speech.commands` import
- `config.conf`
- NVDA 專屬事件通知
- `taskManager` 中的 NVDA 通知轉送

### 可以先包住的相依

- `nvwave`
- `languageHandler`
- `addonHandler`
- 資源與路徑搜尋

這些高風險點可以先限制在 `VE` backend 內部處理，不讓它們擴散到 client 其他層。

### 這一版先不要碰的相依

- 其他 `WorldVoice` engines
- NVDA settings ring / dialogs
- global plugin
- say-all / speech hook 類功能

## 建議實作順序

1. 建立 client 端 `speech command` 相容層
2. 改 router / output path，讓完整 sequence 可傳給 backend
3. 拷貝並改 `taskManager`
4. 拷貝 `VE` 相關程式，先讓 import 成立
5. 拆除 `VE` 對 NVDA `speech.commands`、`synthDriverHandler`、事件的硬依賴
6. 打通 `VE.speak(sequence)` 的最小執行路徑
7. 補上 voice / rate / volume / pitch 控制介面
8. 最後補 cancel / pause / index / done 等執行細節

這個順序的目的，是先把資料模型和 backend contract 改對，再處理調度與 driver 移植，最後才補互動控制與事件細節。

## 驗收標準

### 架構驗收

- `nvda-remote-client` 能還原遠端 speech payload 為 NVDA-style speech sequence object list
- active backend 可直接接收完整 sequence，而不是被迫只吃 `NormalizedSpeech`
- client 不負責執行 prosody command 語意

### 行為驗收

- `VE` backend 能在 `speak()` 內逐項處理 sequence
- 至少支援：
  - text
  - `BreakCommand`
  - `PitchCommand`
  - `RateCommand`
  - `VolumeCommand`
- `taskManager` 能執行 speak / break / cancel 的基本調度
- GUI 可選語音、調整速度、音量、音調
- GUI 控制能實際作用到 `VE` backend

### 範圍驗收

- 不需要同時支援其他 `WorldVoice` engines
- 不需要啟動完整 `WorldVoice` core 抽離
- 不需要把 `WorldVoice` 既有 NVDA 宿主功能一併搬進 client

## 測試策略

### 單元測試

- speech payload 到 command object sequence 的還原
- `taskManager` 的 speak / break / cancel / completion 行為
- `VE` backend 對主要 command 的處理
- GUI 控制變更是否正確傳到 backend

### 整合測試

- 遠端送來含文字、break、pitch、rate、volume 的 speech payload
- client 還原後交由 `VE` backend 正常執行
- 調整 voice / rate / volume / pitch 後，後續 speech 確實使用新參數

### 手動驗證

- 使用 `VE` backend 播放遠端語音
- 驗證停頓、語速、音量、音調可感知改變
- 驗證 GUI 選語音與參數控制可即時生效

## 風險與注意事項

- 若在 client 層先把 speech sequence 扁平化，移植 `VE` driver 的價值會被抵消。
- `VE` 的 NVDA 宿主相依可能比表面更多，搬入時應嚴格限制影響範圍。
- 若先搬 driver 再改資料模型，容易卡在 import 與宿主耦合，無法快速打通主路徑。
- 若不在這一版加入最小控制介面，backend 雖可運作，但使用者無法實際控制 voice 與參數。
- `NormalizedSpeech` 在過渡期可能仍需保留給其他簡單 backend 或舊測試使用，但不應再作為 `VE` 路徑的主模型。

## 最終建議

本設計建議先把這次工作定義為一個小範圍、目的明確的移植：在 `nvda-remote-client` 端建立 NVDA speech command 相容層，拷貝並改寫 `WorldVoice` 的 `taskManager` 與 `VE` 程式，讓 client 可以還原遠端 speech sequence，並把完整 sequence 交給 driver 處理。同時補上最小 GUI 控制介面，讓語音、速度、音量與音調能被實際操作。這樣可以在不啟動完整 core 抽離的前提下，先把最有價值的語音能力移進 `nvda-remote-client`。
