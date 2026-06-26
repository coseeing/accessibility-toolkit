# Speech Runtime Settings 與 NVDA Remote Protocol Boundary 設計

## 目標

透過以下三個依序進行的項目，降低啟動流程中的重複，並補完 NVDA Remote 剩餘的
typed 邊界工作：

1. 把 app entrypoint 中共用的 speech runtime settings persistence 抽出來
2. 以 typed event 取代 NVDA Remote 目前基於 dict 的 session / router status flow
3. 圍繞這些 typed event 拆分 NVDA Remote 的 orchestration，讓 app service 變成
   輕薄的 facade

這是一份單一設計文件，內含三個有先後順序的 milestone。每個 milestone 都應能單獨
review 與 merge，但後面的 milestone 會依賴前面的結果。

## 現況

這個 codebase 已經走過較早期的 bootstrap 抽取階段：

- `bootstrap/platform.py`、`bootstrap/output.py` 與 `bootstrap/app_runtime.py`
  已經集中處理共用 runtime wiring
- `application/events.py` 已經包含共用的 typed application event
- 每個 app package 也已經有自己的 app-domain event module
- NVDA Remote 也已經抽出一些聚焦過的 use case，尤其是 control 與
  input-forwarding 行為

目前剩下的主要摩擦點集中在兩個地方：

- 三個 app entrypoint 仍然重複同一套 speech settings 啟動與持久化流程
- NVDA Remote 仍然使用 dict 形狀的 transport / session / router status payload
  作為過渡性事件邊界

## 非目標

這份設計不包含以下工作：

- 修改 config 檔格式，或重新命名已持久化的 speech settings key
- 將 output 架構重設計成完整的 channel bus
- 修改 Access8Graph 的啟動流程、navigation 或 event handling
- 導入通用型 dependency injection container
- 重寫 UI 版面或加入與這三個 milestone 無關的新 UI 功能

雖然 `refactor3.md` 將 Access8Graph 列為後續項目，但本設計刻意不包含它。本文件只處理
該檢視中排在前面的三個優先項目。

## Milestone 順序

Milestone 的順序有其意義：

1. 共用 speech runtime settings persistence
2. NVDA Remote 的 typed protocol event
3. 圍繞 typed event 的 NVDA Remote orchestration 拆分

`M2` 和 `M1` 之間只有間接依賴，但 `M3` 實務上會依賴 `M2`，因為 protocol / event
邊界一旦 typed 化，後續 orchestration 拆分會簡單很多。

---

## Milestone 1：共用 Speech Runtime Settings Persistence

### 意圖

把 `nvda_remote`、`key_echo` 與 `access8graph` entrypoint 中重複的 speech settings
啟動 / 持久化程式碼抽出來，同時不改變現有 config schema，也不改變各 app 的 speech
行為。

### 問題描述

目前每個 app entrypoint 都重複同一套模式：

- 載入設定中的 speech engine id
- 將已儲存的 voice / rate / pitch / volume 套用到目前的 speech engine
- 持久化 speech engine 變更
- 透過 `SpeechSettingsController` 持久化 voice 與 numeric setting 變更

這段邏輯本身不大，但它被複製了三次，也讓啟動流程看起來比實際上更分歧。

### 設計

在 `src/apps/shared/` 下建立一個小型的 shared speech runtime helper，集中處理目前
重複的 saved speech settings 載入與套用政策。

這裡應使用一個小型 coordinator object，名稱定為
`SpeechRuntimeSettingsCoordinator`，而不是把邏輯散落成多個 free function。

這個 helper 應負責：

- 使用各 app 提供的啟動時 engine 選擇政策
- 針對指定 engine id，將已儲存的 speech settings 套用到某個 speech service
- 產生 app entrypoint 需要的 engine-change persistence 行為

這個 helper 不應：

- 知道 UI class
- 了解共用 `SpeechSettingsController` 以外的 app-specific controller 細節
- 修改 config schema
- 改變 `SpeechSettingsController` 目前持久化 voice / rate / pitch / volume 的方式

### 建議檔案結構

- Create: `src/apps/shared/speech_runtime_settings.py`
- Modify: `src/apps/nvda_remote/main.py`
- Modify: `src/apps/key_echo/main.py`
- Modify: `src/apps/access8graph/main.py`
- Modify: `tests/unit/test_bootstrap_app_runtime.py` 或其他已存在、負責驗證 app 啟動組裝的 runtime 測試
- Create: `tests/unit/test_speech_runtime_settings.py`

### Shared Helper 行為

這個 shared helper 應封裝目前三個 entrypoint 中重複的啟動政策：

- `SpeechEngineConfigStore.load_engine_id(default_engine_id=...)`
- 載入所選 engine 對應的已儲存 voice / rate / pitch / volume
- 驗證已儲存的 voice 是否存在於目前 engine 的 `list_voices()`
- 只套用該 engine 支援的 numeric setting
- 建立 engine-change callback，在 engine 切換時持久化目前選擇，並重新套用已儲存設定
- 保留各 app 目前的啟動 engine 選擇行為，包括像 `key_echo` 這種固定 engine 的情況

這個 helper 應從 app 啟動程式碼呼叫，而不是放進 UI layer。

### M1 後 App Entrypoint 應保留的責任

每個 `main.py` 仍然應該：

- 決定 app-specific 的預設 engine 行為
- 建立 app service
- 在建立 app service 時傳入共用的 speech settings callback
- 建立 UI app 與 keyboard input service

每個 `main.py` 不應再：

- 自己定義一份 private `_apply_saved_speech_settings()` 複本
- 重複寫 engine 切換後的 save-and-reapply 邏輯
- 各自手寫同一套 load / apply / persist 流程

### 驗證條件

當以下條件都成立時，`M1` 才算完成：

- 重複的 speech settings 啟動邏輯只存在於一個 shared helper 中
- 各 app entrypoint 明顯變薄
- 啟動時仍能正確還原所選 engine 與其設定
- engine 切換後仍會持久化並重新套用已儲存設定
- 既有啟動 / runtime 測試持續通過

---

## Milestone 2：NVDA Remote Typed Protocol Event

### 意圖

把 `RemoteSession` 與 `MessageRouter` 目前使用的 dict-based status flow 改成
typed protocol event，讓 NVDA Remote 不再依賴 JSON 形狀的過渡性 status contract。

### 問題描述

NVDA Remote 目前的 event 邊界只 typed 化了一半：

- `RemoteSession` 會發出 connection state 的 dict payload
- `MessageRouter` 會發出 protocol message 與 invalid input 的 dict payload
- `NvdaRemoteAppService` 會再透過 `StatusEvent.from_payload()` 轉換這些 dict

這讓 protocol contract 變成隱性的，也迫使 app service 持續承擔 event parsing 的責任。

### 設計

在 `src/interop/protocol/` 下加入一個 typed protocol event module，供
`RemoteSession` 與 `MessageRouter` 共用。Protocol layer 應直接發出 typed dataclass，
而不是再繼續發出 dict-shaped status payload。

Event model 應涵蓋目前 session / router 的情境，dataclass 名稱可沿用現有語意，
例如：

- `RemoteSessionConnected`
- `RemoteSessionDisconnected`
- `RemoteSessionVersionMismatch`
- `RemotePeerMessageReceived`
- `RemoteProtocolMessageIgnored`
- `RemoteProtocolMessageInvalid`

### 建議檔案結構

- Create: `src/interop/protocol/events.py`
- Modify: `src/interop/protocol/session/remote_session.py`
- Modify: `src/interop/protocol/routing/message_router.py`
- Modify: `src/apps/nvda_remote/service.py`
- Modify: `tests/unit/test_message_router.py`
- Create: `tests/unit/test_remote_session.py`
- Modify: `tests/unit/test_nvda_remote_app_service.py`
- Modify: `tests/unit/test_application_events.py`，但只限於它仍然測到過渡用 `StatusEvent` helper 的情況

目前放在 `tests/unit/test_message_router.py` 裡的 `RemoteSession` coverage，應移到新的
`tests/unit/test_remote_session.py`，讓 router 與 session 契約能分開演進。

### 邊界規則

Protocol layer 應負責：

- 判斷某個 payload 是 session event、remote peer message，還是 invalid protocol message
- 發出 typed protocol event

App layer 應負責：

- 視需要把 protocol event 映射成既有的 app-domain event
- 更新 app state
- 決定哪些 event 要對 UI 顯示

Protocol layer 不應：

- 知道 wx
- 知道 app-specific UI state
- 知道 `SpeechSettingsController`
- 再把 protocol event 轉回 dict

### 過渡期相容性

在遷移過程中，`StatusEvent` 可以暫時保留為相容性 helper，但當這個 milestone 完成時，
它不應再出現在 production path 中。

### 驗證條件

當以下條件都成立時，`M2` 才算完成：

- `RemoteSession` 與 `MessageRouter` 發出的是 typed event，而不是 dict payload
- `NvdaRemoteAppService` 在正常 protocol flow 中不再依賴 `StatusEvent.from_payload()`
- 剩餘的 app-level event mapping 是明確且 typed 的
- router 與 session 測試改為驗證 typed event，而不是驗證原始 dict 形狀

---

## Milestone 3：NVDA Remote Orchestration 拆分

### 意圖

以 `M2` 產生的 typed protocol event 為基礎，將 NVDA Remote 剩餘的 orchestration
責任拆成較小的單元，讓 `NvdaRemoteAppService` 回到作為 UI 與 runtime wiring facade
的角色。

### 問題描述

`NvdaRemoteAppService` 目前仍承擔過多責任：

- transport binding
- session lifecycle
- router lifecycle
- connection state transition
- control start / stop orchestration
- remote status translation
- capture 與 hotkey policy
- clipboard push
- tone handling

即使已有部分 use case 被抽出，這個 service 仍然是整體架構的重心。

### 設計

把剩餘 orchestration 拆成聚焦的單元，並透過 typed event 與小型 callback 介面互動。

Service 本體應只保留 UI-facing orchestration surface，其餘責任都委派出去。

優先要抽出的責任包括：

- connection / disconnection orchestration
- protocol event handling，以及它到 app event 的轉換
- status presentation / dispatch 到 UI 邊界

Key forwarding 與 control mode 若目前切分已足夠，可先保留在既有 use case 中。

### 建議檔案結構

- Modify: `src/apps/nvda_remote/service.py`
- Create: `src/apps/nvda_remote/use_cases/connection.py`
- Create: `src/apps/nvda_remote/use_cases/protocol_events.py`
- Create: `src/apps/nvda_remote/use_cases/status_presentation.py`
- Reuse: `src/apps/nvda_remote/use_cases/control_mode.py`
- Reuse: `src/apps/nvda_remote/use_cases/input_forwarding.py`
- Modify: `tests/unit/test_nvda_remote_app_service.py`
- Modify: `tests/unit/test_nvda_remote_use_cases.py`
- Create or update: 其他聚焦於新 use-case module 的測試

### M3 後的 Service 邊界

`NvdaRemoteAppService` 仍應保留 UI 需要使用的 controller method，但不應再是
protocol payload parsing 與 connection-state orchestration 的所在地。

它主要應該負責：

- 將較小的 use case 接起來
- 對 UI 暴露 app controller API
- 將 typed event 轉交給 UI listener
- 將 main-thread dispatch glue 集中在同一處

### 驗證條件

當以下條件都成立時，`M3` 才算完成：

- `NvdaRemoteAppService` 明顯比原本更薄
- connection 與 protocol event handling 已有專屬單元
- service 本體不再承擔 dict parsing 或 dict-shaped status translation
- 從使用者角度看，UI 行為沒有改變
- 既有 NVDA Remote 測試在新的 event 邊界下仍然通過

---

## 跨里程碑測試策略

實作時應使用小而聚焦的測試來覆蓋每個 milestone。

### M1 測試

- 驗證 shared helper 會把已儲存的 speech settings 套用到目前 engine
- 驗證 engine 切換會持久化並重新套用已儲存設定
- 驗證每個 app entrypoint 仍然能成功建立 runtime

### M2 測試

- 驗證 `RemoteSession` 會發出 typed session event
- 驗證 `MessageRouter` 對有效與無效輸入都會發出 typed protocol event
- 驗證 `NvdaRemoteAppService` 消費的是 typed event，而不再依賴 dict payload 形狀

### M3 測試

- 驗證新的 connection / protocol / status 單元能處理原本 service 處理的情境
- 驗證 UI-facing app service API 維持穩定
- 驗證這次拆分沒有改變既有 control 或 forwarding 行為

## 完成定義

當以下條件都成立時，這份設計才算完成：

- speech runtime settings persistence 不再重複出現在三個 app entrypoint 中
- NVDA Remote 的 protocol / session / router flow 已端到端 typed 化
- NVDA Remote 的 orchestration 已圍繞 typed 邊界拆成較小單元
- 既有 app-facing 行為保持穩定
- 產出的程式碼仍符合目前 repo 的 source layout 與測試風格
