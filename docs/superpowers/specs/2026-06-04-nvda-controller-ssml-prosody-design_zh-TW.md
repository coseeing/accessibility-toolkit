# NVDA Controller SSML Prosody Design

## 概述

本文件定義 `nvda-remote-client` 針對 `NvdaControllerSpeechOutput` 的下一步設計：不再只把 speech sequence 扁平化成文字並呼叫 `nvdaController_speakText`，而是改成將本地 `SpeechSequence` 轉為 SSML，交由 `nvdaController_speakSsml` 送入 NVDA。此變更的目的，是讓 `BreakCommand`、`PitchCommand`、`RateCommand`、`VolumeCommand` 可以在 NVDA Controller backend 路徑中保留並生效。

本次設計同時補齊本地 prosody command model，讓 `PitchCommand`、`RateCommand`、`VolumeCommand` 都能表達 `offset` 與 `multiplier` 兩種形式，且遠端 payload 的 restore 層也能接受這兩種格式。

## 目標

- 將 `NvdaControllerSpeechOutput` 的 speak 路徑從 `nvdaController_speakText` 改為 `nvdaController_speakSsml`。
- 讓 `BreakCommand` 可透過 SSML `<break>` 映射後由 NVDA 端還原並執行。
- 讓本地 `PitchCommand`、`RateCommand`、`VolumeCommand` 都支援 `offset` 與 `multiplier`。
- 讓遠端 payload restore 對 `PitchCommand`、`RateCommand`、`VolumeCommand` 都接受 `offset` 或 `multiplier`。
- 在 speech backend 層明確建立本地 `rate/pitch/volume` 狀態，作為 UI 顯示值與 prosody baseline。

## 不在這份設計內的範圍

- 不新增 `nvdaControllerClient` 的原生 setter API；它本身沒有 `setRate` / `setPitch` / `setVolume` 這類函式。
- 不改 NVDA Remote protocol。
- 不重做整套 speech command model 成完全等同 NVDA `speech.commands`。
- 不改 `pyttsx3` backend 的整體架構，只調整它與 prosody model 的一致性。
- 不處理所有 NVDA speech command，只聚焦 `BreakCommand`、`PitchCommand`、`RateCommand`、`VolumeCommand`。

## 背景與問題

目前 `NvdaControllerSpeechOutput` 的實作只會：

- 從 `SpeechSequence` 中抽取文字
- 用空白串接
- 呼叫 `nvdaController_speakText`

這種做法會直接遺失：

- `BreakCommand`
- `PitchCommand`
- `RateCommand`
- `VolumeCommand`

另一方面，`nvdaControllerClient` 本身雖然沒有獨立的 prosody setter API，但它提供 `nvdaController_speakSsml`，而 NVDA 端會把 SSML 解析成 speech sequence 再送入 `speech.speak(...)`。因此正確方向不是期待 controller client 提供 `setRate` / `setPitch` / `setVolume`，而是讓 client 端把本地 sequence 轉為 SSML。

## 核心設計決策

### 1. `NvdaControllerSpeechOutput` 改走 `speakSsml`

`NvdaControllerSpeechOutput.speak()` 應改用 `nvdaController_speakSsml`，不再使用 `nvdaController_speakText` 當主要 speak 路徑。`nvdaController_speakText` 可保留作為 fallback 或歷史常數，但正常 speak 流程應以 SSML 為主。

### 2. Prosody command model 一次補齊

本地 `PitchCommand`、`RateCommand`、`VolumeCommand` 都應支援：

- `offset`
- `multiplier`

規則如下：

- 允許只指定 `offset`
- 允許只指定 `multiplier`
- 允許兩者都不指定，代表回到預設
- 不允許兩者同時指定為非預設值

這讓本地模型在語意上更接近 NVDA `BaseProsodyCommand`，避免不同 prosody command 的表示方式不一致。

### 3. 遠端 payload restore 也一起補齊

既然 model 補成完整，restore 層也要同步補齊。遠端 payload 應接受：

- `["PitchCommand", {"offset": 10}]`
- `["PitchCommand", {"multiplier": 1.2}]`
- `["RateCommand", {"offset": 10}]`
- `["RateCommand", {"multiplier": 1.2}]`
- `["VolumeCommand", {"offset": 10}]`
- `["VolumeCommand", {"multiplier": 0.8}]`

本地 restore 時要保留原始語意，而不是強迫轉成單一表示法。

### 4. 每個 backend 都要持有本地 prosody state

`rate`、`pitch`、`volume` 不只是 UI 欄位，而是每個 speech backend 的本地狀態。這份 state 既是：

- UI 顯示與修改的來源
- `offset` 型 command 的 baseline

`pyttsx3` backend 目前已持有這些值，但尚未正式被定義為 baseline 機制。`NvdaControllerSpeechOutput` 則需要補上相同狀態。

### 5. `offset` 換算以 backend local state 為基準

由於 `nvdaControllerClient` 無法直接讀取遠端 NVDA synth 的實際 prosody baseline，因此本次設計採用：

- backend 目前持有的 `rate/pitch/volume` 值
- 作為 `offset -> multiplier -> SSML 百分比` 的換算基準

這代表它不是「遠端 NVDA 真實設定」的精準鏡像，而是本地可預期且一致的 baseline。

## 架構與責任邊界

### `interop.models.speech_commands`

負責：

- 定義 `PitchCommand`、`RateCommand`、`VolumeCommand` 的資料模型
- 驗證 `offset` / `multiplier` 的合法組合
- 保留原始表示語意

不負責：

- 實際 backend 參數套用
- SSML 輸出

### `interop.serializer`

負責：

- 在反序列化時還原 `PitchCommand`、`RateCommand`、`VolumeCommand` 的兩種表示格式

不負責：

- prosody 效果換算

### `adapters.windows.nvda_controller`

負責：

- 持有本地 `rate/pitch/volume` 狀態
- 將 `SpeechSequence` 轉為 SSML
- 呼叫 `nvdaController_speakSsml`

不負責：

- 直接模擬 NVDA synth driver 行為
- 讀取遠端 NVDA 真實 synth 設定

## Prosody Model 規則

建議將 `PitchCommand`、`RateCommand`、`VolumeCommand` 統一成同樣的建構規則：

- `offset=10, multiplier=1.0`：合法，代表 offset 模式
- `offset=0, multiplier=1.2`：合法，代表 multiplier 模式
- `offset=0, multiplier=1.0`：合法，代表回預設
- `offset=10, multiplier=1.2`：不合法，應丟出 `ValueError`

每個 command 應能讓 consumer 判斷目前是：

- `offset` 模式
- `multiplier` 模式
- `default` 模式

實作上可透過：

- `mode` 屬性
- 或等價的 helper method / property

來避免 backend 自己重複猜測。

## Backend Prosody State

每個 speech backend 都應持有本地狀態：

- `voice`
- `rate`
- `pitch`
- `volume`

這些值的角色有兩個：

1. 提供 GUI 顯示與 setter/getter
2. 作為 `offset` 型 command 的 baseline

在 `pyttsx3` backend 中，這些值已經存在；在 `NvdaControllerSpeechOutput` 中，則需要從目前的 no-op getter/setter 改為真實持有狀態的實作。

## `SpeechSequence -> SSML` 映射規則

### 文字

`str` 項目直接輸出為文字節點，需做基本 XML escape。

### `BreakCommand`

`BreakCommand(time=200)` 輸出為：

```xml
<break time="200ms"/>
```

### `PitchCommand` / `RateCommand` / `VolumeCommand`

一律輸出為：

```xml
<prosody pitch="120%">...</prosody>
<prosody rate="80%">...</prosody>
<prosody volume="110%">...</prosody>
```

其中百分比的決定方式如下：

- 若 command 以 `multiplier` 表示，直接轉成百分比
- 若 command 以 `offset` 表示，先以 backend 目前值計算新值，再換算成相對 baseline 的百分比

### reset/default

當 command 代表回到預設時，應在 SSML 生成流程中移除對應 prosody attribute，讓後續文字不再帶該屬性。

## 資料流

1. 遠端 payload 進入 `JSONSerializer.deserialize()`
2. serializer 還原 prosody command，接受 `offset` 或 `multiplier`
3. `MessageRouter` / `OutputManager` 將完整 `SpeechSequence` 交給 active backend
4. `NvdaControllerSpeechOutput` 以本地 prosody state 為基準，將 sequence 轉為 SSML
5. backend 呼叫 `nvdaController_speakSsml`
6. NVDA 端將 SSML 解析回 speech sequence 並執行

## 錯誤處理

- 若 prosody command 同時帶有非預設 `offset` 與 `multiplier`，應在本地模型建立時直接拒絕。
- 若 `nvdaController_speakSsml` 無法呼叫或 DLL 不可用，應記錄 log 並安全返回，不可讓 client 崩潰。
- 若 sequence 中含有目前未支援轉換的 command，應安全略過，不可讓整段 speech 失敗。
- 若 SSML 生成過程遇到不合法文字，應做 XML escape，而不是直接拼接原字串。

## 測試策略

需要補的測試分為四類：

1. `speech_commands` 單元測試
   驗證 `PitchCommand`、`RateCommand`、`VolumeCommand` 的 `offset/multiplier` 規則、非法組合與 restore 行為。

2. `serializer` 單元測試
   驗證遠端 payload 對三種 prosody command 都可接受 `offset` 與 `multiplier`。

3. `nvda_controller` 單元測試
   驗證：
   - backend 會呼叫 `nvdaController_speakSsml`
   - `BreakCommand` 會轉為 `<break>`
   - prosody command 會轉為 `<prosody ...="N%">`
   - backend getter/setter 狀態可作為 baseline

4. 回歸測試
   驗證現有 `pyttsx3` backend 不被破壞，且 `SpeechSequence` 路徑仍正常。

## 成功標準

- `NvdaControllerSpeechOutput` 不再以 `speakText` 作為主要 speak 路徑。
- `BreakCommand` 可在 `nvdaController` backend 路徑中保留並映射為 SSML break。
- `PitchCommand`、`RateCommand`、`VolumeCommand` 本地模型都支援 `offset/multiplier`。
- 遠端 payload restore 三者都支援 `offset/multiplier`。
- `NvdaControllerSpeechOutput` 持有本地 `rate/pitch/volume` 狀態。
- `offset` 型 prosody command 能依 backend 目前值換算成 SSML 百分比。
- 不支援的 command 不會讓 `speak()` 崩潰。
- 既有 `pyttsx3` backend 路徑維持可用。
