# WorldVoice Core Extraction Design

## 概述

本文件定義一個重構方向：將 `WorldVoice` 從目前高度耦合 NVDA runtime 的 synth driver，拆分成一個可重用的 host-agnostic speech core，以及宿主專用的 adapter 層。這次重構的主要目的不是單純整理 `WorldVoice` 內部程式碼，而是要讓同一套語音核心能同時服務 NVDA add-on 與 `nvda-remote-client`，並為未來延伸到 Linux、macOS、iOS、Android 的宿主整合保留正確邊界。

第一階段的實作仍留在 `WorldVoice` repo 內進行。`WorldVoice` 既有的 NVDA 使用情境必須保留，而 `nvda-remote-client` 將在後續階段接入同一套核心。新的核心輸入模型以 NVDA-style speech sequence 為主，而不是 `nvda-remote-client` 目前的 `NormalizedSpeech`。

## 目標

- 建立一個不直接依賴 NVDA runtime 的 `WorldVoice` 語音核心。
- 讓 `taskManager`、`VoiceManager`、engine lifecycle、speech pipeline、settings、speech events 進入核心層。
- 讓 `WorldVoice` 的 NVDA 整合改為 adapter，而不是核心前提。
- 讓 `nvda-remote-client` 能重用 `WorldVoice` core，作為完整 speech backend，而不只是單純呼叫 speak。
- 將核心設定來源從 `config.conf` 轉為單一 JSON 設定檔。
- 保留與 NVDA 生態相近的資料語意，因此核心以 NVDA-style speech sequence 作為主要輸入模型。
- 第一階段 driver 支援聚焦在 `VE` 與 `pyttsx3`，避免同時重構所有 engine。

## 不在這份設計第一階段內的範圍

- 直接把 `WorldVoice` core 抽成獨立新 repo 或公開新 package。
- 一次完成 Linux、macOS、iOS、Android 宿主實作。
- 將 NVDA 專屬 UI 直接搬進 `nvda-remote-client`。
- 重寫 `WorldVoice` 的所有語音引擎 driver。
- 第一階段就讓所有既有 WorldVoice engines 全部完成 core 化。
- 修改 NVDA Remote protocol。

## 背景與問題

目前 `WorldVoice` 的核心流程與 NVDA runtime 緊密耦合，具體包含：

- 直接使用 `config.conf` 與 config spec 作為主要設定來源。
- 直接依賴 `synthDriverHandler.getSynth()`、`synthIndexReached`、`synthDoneSpeaking`。
- synth driver 入口同時承擔 speech flow control、voice 管理、pipeline 套用、事件通知與 NVDA UI 整合。
- `taskManager` 與 `VoiceManager` 都直接感知 NVDA 環境，無法被其他宿主直接重用。

這種結構的問題不是只有耦合度高，而是會直接阻礙產品核心目標。這個專案希望把控制 NVDA 遠端機器的語音輸出能力移植到不只 Windows 的宿主與客戶端上。如果核心架構仍以 NVDA runtime 為前提，後續不論是 `nvda-remote-client`、Linux、macOS、iOS 或 Android，都必須重新實作一套語音管線與管理邏輯。

## 核心設計決策

### 1. 採用完整核心抽離，而不是局部抽模組

這次重構採用完整的 host-agnostic core 設計，而不是只先抽 `taskManager`、`VoiceManager` 或 settings。原因是 `nvda-remote-client` 需要的是完整 speech backend 能力，包括任務調度、voice 選擇、pipeline、設定與事件，而不是幾個可重用的零件。

### 2. 核心輸入使用 NVDA-style speech sequence

新的核心第一版以 NVDA-style speech sequence 為主要輸入模型。這樣可以保留與 NVDA 生態的語意一致性，降低 `WorldVoice` 既有行為的遷移成本，也避免為了 `nvda-remote-client` 單獨定義另一套主模型。

`nvda-remote-client` 如果要使用 `WorldVoice` core，應由 client adapter 將 remote speech 轉換為核心可接受的 speech sequence。

### 3. 核心設定來源改為單一 JSON 檔

設定不再以 `config.conf` 為核心真實來源。新的核心應只知道一個單一 JSON 設定檔，內容包含 voice、engine、pipeline、wait factor 與其他必要參數。NVDA adapter 在過渡期可負責將 `config.conf` 與 JSON 同步，但 JSON 必須是 core 的主資料來源。

### 4. 第一階段仍留在 WorldVoice repo 內

這次不先拆獨立 repo。新的核心仍放在 `WorldVoice` repo 中完成重構，再由 `nvda-remote-client` 透過 path dependency、vendor 或其他內部引用方式接入。這樣可以先把核心做對，再決定未來是否獨立發佈。

### 5. Driver 收斂策略採最小可行覆蓋

第一階段不追求所有既有 `WorldVoice` engines 同步完成抽離。新的 core 應先以兩條代表性路徑為目標：

- `VE`
- `pyttsx3`

選這兩條路徑的原因是：

- `VE` 代表 `WorldVoice` 既有的重要 NVDA 生態整合能力。
- `pyttsx3` 代表一條不依賴 NVDA runtime、且更容易被 `nvda-remote-client` 直接重用的通用本機 TTS 路徑。

第一階段只要能讓這兩個 driver 路徑透過同一套 `worldvoice_core` 運作，就足以驗證核心邊界是否正確。其他 engines 應在後續階段逐步遷移，而不是在第一輪一起納入。

## 建議架構

建議在 `WorldVoice` repo 內建立三層結構：

- `worldvoice_core`
- `worldvoice_nvda`
- `worldvoice_client_adapter`

### `worldvoice_core`

純核心層，不直接依賴 NVDA runtime。

職責：

- 接收 NVDA-style speech sequence
- 管理 speech task scheduling
- 管理 voice registry、voice selection、instance cache
- 管理 engine discovery 與 lifecycle
- 執行 speech sequence pipeline transform
- 讀寫 JSON 設定
- 發出宿主中立的 speech 與 settings 事件

### `worldvoice_nvda`

NVDA 宿主 adapter。

職責：

- 提供 NVDA `SynthDriver` 入口
- 與 `config.conf` 橋接
- 將 core event 轉成 `synthIndexReached`、`synthDoneSpeaking`
- 整合 NVDA settings ring、dialogs、global plugin、speech hook
- 將 NVDA runtime 需求轉為 core 可接受的呼叫

### `worldvoice_client_adapter`

給 `nvda-remote-client` 使用的宿主 adapter。

職責：

- 將 remote speech 轉成 NVDA-style speech sequence
- 建立並控制 `SpeechRuntime`
- 將 core settings 對接到 client 端設定與 UI
- 消費 core event，供 client 更新狀態或輸出控制

## 核心元件設計

### `SpeechRuntime`

這是核心入口，也是宿主唯一應直接操作的主要物件。

職責：

- 接收 speech sequence
- 協調 pipeline 處理
- 決定 voice 選擇與 engine 呼叫
- 管理 speak / cancel / pause / stop
- 將事件轉交給 `EventHub`

它要取代目前分散在 `WorldVoice` `SynthDriver` 入口中的流程控制。

### `TaskManager`

保留目前 `taskManager.py` 的主要價值：

- 任務序列化
- `SpeechFuture`
- cancel token
- break task
- speech task timeout

但必須移除對下列內容的直接依賴：

- `synthIndexReached`
- `synthDoneSpeaking`
- `getSynth()`

新的 `TaskManager` 只處理任務生命週期與執行狀態，不知道 NVDA 是哪個宿主。

### `VoiceManager`

保留目前 `voiceManager.py` 的主要責任：

- enabled engine 篩選
- voice catalog 建立
- default voice 決策
- voice instance cache
- voice parameter consistency
- engine lifecycle coordination

但它不能再直接依賴：

- `config.conf`
- `languageHandler`
- `VoiceInfo`
- NVDA 型別或 UI 設定概念

新的 `VoiceManager` 應以核心自有型別運作，例如：

- `VoiceProfile`
- `VoiceCatalog`
- `EngineDescriptor`
- `CoreSettings`

第一階段 `VoiceManager` 的 engine 啟用與 voice catalog 驗證，也應優先只保證 `VE` 與 `pyttsx3` 兩條路徑可正常運作。其餘 engine 可以先保留為未遷移狀態，只要不阻塞核心 API 定義即可。

### `PipelineProcessor`

收攏目前 `pipeline/*` 與 `pipeline/settings.py` 的主要邏輯。

職責：

- 對 speech sequence 做語言、數字、pause、ordering 相關 transform
- 套用 pipeline settings
- 產出最後送往 voice / engine 的 sequence

它可以保留 NVDA-style command 語意，但不能直接依賴 NVDA hook 或 speech filter runtime。

### `SettingsStore`

第一版以單一 JSON 檔為主。

職責：

- load
- save
- validate
- migrate

其他模組不應直接依賴 JSON 細節，而應只接觸 `CoreSettings` 物件。

### `EventHub`

提供宿主中立事件模型，取代目前直接綁定 NVDA extension point 的方式。

至少應支援以下事件：

- speech started
- index reached
- speech finished
- speech cancelled
- voice changed
- settings changed

NVDA adapter 會把它翻譯成 NVDA event。`nvda-remote-client` 則會用它驅動自己的狀態與控制。

## 資料流

建議資料流固定如下：

1. 宿主 adapter 建立 `SpeechRuntime`
2. adapter 載入 `CoreSettings`
3. adapter 提交 speech sequence
4. `SpeechRuntime` 呼叫 `PipelineProcessor`
5. `VoiceManager` 根據 sequence、locale、settings 選擇 voice instance
6. `TaskManager` 排程 speak / break / cancel 任務
7. engine instance 執行實際語音輸出
8. engine callback 透過 `EventHub` 發送事件
9. adapter 視宿主需求轉換為 NVDA 或 client 事件

這個流程的重點是，宿主不再掌控內部語音流程。NVDA 與 `nvda-remote-client` 只負責橋接，不再各自擁有一套獨立 speech runtime。

## NVDA Adapter 邊界

以下內容必須留在 `worldvoice_nvda`，不得進入核心：

- `SynthDriver` 與 NVDA driver lifecycle
- `config.conf` 與 config spec 註冊
- `synthIndexReached`、`synthDoneSpeaking`、`getSynth()`
- NVDA settings ring、voice settings dialogs、global plugin
- `speech.extensions.filter_speechSequence` 與其他 NVDA speech hook
- say-all 與其他 NVDA 專屬整合流程

以下內容應進入 `worldvoice_core`：

- `TaskManager`
- `VoiceManager`
- engine discovery / lifecycle
- pipeline settings 與 sequence transform
- voice parameter persistence
- speech event model

判斷原則很簡單：凡是必須依靠 NVDA runtime 才能存在的行為，應留在 adapter；凡是可由任意宿主重複使用的行為，應進核心。

## 設定模型

第一版設定來源使用單一 JSON 檔。它至少應包含：

- default voice
- per-voice settings
- engine enablement
- pipeline scope
- wait factor 相關參數
- auto language switching 相關參數

第一階段 JSON 設定也應至少能描述 `VE` 與 `pyttsx3` 所需的 engine enablement、default voice 與 per-voice settings。其他 engine 的設定欄位可在後續 migration 中逐步補齊。

建議原則：

- JSON 是核心唯一主來源
- NVDA adapter 可在過渡期進行匯出或同步
- core 不應直接 import 或查詢 `config.conf`

這樣可讓未來宿主直接提供同一份設定模型，而不需要複製 NVDA 的 config 行為。

## 與 nvda-remote-client 的整合方向

`nvda-remote-client` 的第一波目標不是只做到「能發出聲音」，而是將 `WorldVoice` 作為完整 speech backend 架構接入。

第一波整合應包含：

- 本機 speech output
- voice selection
- rate / pitch / volume
- pipeline settings
- task scheduling
- settings load/save
- speech event consumption

第一波整合的 driver 範圍先以 `pyttsx3` 為 `nvda-remote-client` 直接可用目標，並保留 `VE` 在 core 中的支援與驗證能力。是否在 `nvda-remote-client` 第一版就直接暴露 `VE`，可以在 implementation plan 階段依實際宿主依賴條件再決定，但核心 API 必須從一開始就能容納這兩條路徑。

不應只做一條最小 speak path，否則後續仍要在 client 側重建 voice 與 pipeline 邏輯，失去這次重構的主要價值。

## 分階段交付

### Phase 1: Core extraction inside WorldVoice

在 `WorldVoice` repo 內建立 `worldvoice_core`，先抽出：

- `SpeechRuntime`
- `TaskManager`
- `VoiceManager`
- `PipelineProcessor`
- `SettingsStore`
- `EventHub`

這一階段的成功標準是，NVDA adapter 已可開始委派給 core，但不要求 `nvda-remote-client` 當下立即接入。此外，核心設計與最小驗證必須至少覆蓋 `VE` 與 `pyttsx3`。

### Phase 2: NVDA adapter rewire

將目前 `WorldVoice` 的 synth driver 主流程改為委派給 core。

成功標準：

- 既有 NVDA 使用情境不退化
- `VE` 路徑已能透過 core 驅動
- voice selection 仍可用
- rate / pitch / volume 仍可用
- pipeline settings 仍可用
- index / done speaking 事件仍可運作

### Phase 3: JSON settings migration

將 core 設定改為 JSON 主來源。

成功標準：

- core 不直接依賴 `config.conf`
- adapter 只做橋接與同步
- 主要語音與 pipeline 邏輯不再讀取 NVDA config section

### Phase 4: nvda-remote-client integration

讓 `nvda-remote-client` 加入 `WorldVoice` backend adapter，直接使用 `worldvoice_core`。

成功標準：

- `nvda-remote-client` 不直接 import NVDA runtime
- voice manager、task scheduling、pipeline、settings、events 都走同一套 core
- backend 切換與 client 設定能控制 `WorldVoice` core
- `pyttsx3` 路徑可作為 `nvda-remote-client` 第一個完整接入的 backend

## 驗收標準

### 架構驗收

- `worldvoice_core` 不 import `config`、`synthDriverHandler`、`speech.extensions`、`gui`、`addonHandler`
- `worldvoice_nvda` 只承擔宿主橋接責任
- `nvda-remote-client` 不需要依賴 NVDA runtime 即可使用 `WorldVoice` core

### 行為驗收

- NVDA 中既有 `WorldVoice` 核心功能不退化
- `VE` 在 NVDA 宿主中可透過新 core 正常運作
- `pyttsx3` 在 `nvda-remote-client` 中可作為完整 speech backend 使用
- `taskManager`、`VoiceManager`、pipeline、settings 在兩個宿主中走同一套邏輯

### 遷移驗收

- 單一 JSON 設定檔可作為核心主來源
- `config.conf` 僅存在於 NVDA adapter
- 新宿主若要接入，只需提供 adapter，不需再拆 core

## 測試策略

### 核心單元測試

- `TaskManager` 的 speak / break / cancel / timeout
- `VoiceManager` 的 voice catalog、default voice、instance cache
- `PipelineProcessor` 的 sequence transform
- `SettingsStore` 的 load / save / validate / migrate
- `EventHub` 的事件發送與監聽
- `VE` 與 `pyttsx3` 的 engine descriptor / voice registration / lifecycle

### NVDA Adapter 測試

- core event 是否正確轉成 NVDA event
- JSON 與 `config.conf` 的橋接是否符合預期
- `SynthDriver` 是否已正確委派給 core

### nvda-remote-client 測試

- `WorldVoice` backend 是否可被建立與切換
- speech sequence 是否能正確送進 core
- settings 與 voice 控制是否可透過 client 層生效

## 風險與注意事項

- `WorldVoice` 目前核心與 NVDA runtime 的耦合範圍很廣，若沒有先定義清楚 API，就容易把舊依賴搬進新 core。
- 若先做最小 speak path 而不把 voice、pipeline、settings 一起納入，後面幾乎一定要做第二次大重構。
- JSON 設定遷移若沒有明確定義主來源，容易出現 `config.conf` 與 JSON 雙真實來源衝突。
- `nvda-remote-client` 若直接繞過 core 自行處理部分語音流程，會破壞這次重構的主要價值。
- 若第一階段同時要求所有 engines 遷移，範圍會明顯失控，且會稀釋對 `VE` 與 `pyttsx3` 兩條代表性路徑的驗證深度。

## 最終建議

本設計建議 `WorldVoice` 採用完整的 host-agnostic core 重構策略，在 repo 內建立新的 core 層，並以 NVDA-style speech sequence、單一 JSON 設定檔與宿主 adapter 邊界為核心原則。`WorldVoice` 自身先完成 NVDA adapter 重接，再讓 `nvda-remote-client` 以完整 speech backend 的方式接入。這樣的拆法才能讓語音核心成為真正可移植、可重用的產品資產，而不是只服務單一 NVDA add-on 的內部模組。
