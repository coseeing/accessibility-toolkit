# App Layer 邊界指引

## 目的

本文件定義一套實務上的判準，用來判斷哪些內容應優先抽成共享基礎設施，哪些內容目前可以先留在 app service 內。

主要目標：未來新增 app 時，可以重用 input/output 基礎架構，而不需要依賴 `nvda_remote` 的特定行為。

## 核心原則

如果某段邏輯代表的是可重用的 capability、policy 或 lifecycle，而且其他 app 很可能會原樣需要它，就應該優先抽成共享程式碼。

如果某段邏輯明顯屬於該 app 的 workflow、UI 語意或 remote business rule，就先留在 app service 內。

## 應優先抽共用

這些比起立刻大幅拆分 `NvdaRemoteAppService`，更應該先移到共享層。

### 1. 平台與 adapter resolution

應從 app entrypoint 抽出：
- `sys.platform == "darwin"` 或 `win32` 這類平台判斷
- Windows / macOS adapter 的 lazy loading
- keyboard capture、hotkey capture、clipboard、speech backend factory 的 runtime 選擇

原因：
- 每個新 app 都會面對同樣的 wiring 問題
- 這是 infrastructure，不是 app logic

目前來源：
- `src/apps/nvda_remote/main.py`
- `src/apps/key_echo/main.py`

### 2. 輸入生命週期抽象

應抽出共享控制：
- input capture 的 start / stop
- hotkey capture 的 start / stop
- attach listener / handler 的語意
- 共享的 normalized key event pipeline

原因：
- 多個 app 都會需要輸入擷取生命週期
- app 應消費 input service，而不是自己管理低階 capture setup

目前來源：
- `src/application/keyboard.py`
- `src/adapters/inputs/base.py`
- `src/apps/nvda_remote/service.py` 的部分邏輯

### 3. 輸出 capability contract

應抽出並穩定化：
- speech playback contract
- tone output contract
- wave output contract
- braille output contract
- backend registry / capability discovery

原因：
- 這才是未來 app 真正要重用的基礎架構
- 目前結構仍然過度以 speech 為中心

目前來源：
- `src/adapters/outputs/interfaces.py`
- `src/application/output_service.py`
- `src/application/output_capabilities.py`
- `src/application/speech_backends.py`

### 4. Typed 共享 capability / runtime event

應抽出共享 event model，但只限於可重用的 capability / runtime concern，例如：
- input capture started / stopped
- hotkey capture started / stopped
- error notification
- speech backend change
- clipboard availability

原因：
- 未來 app 不應依賴 ad hoc 的 `dict` payload
- typed event 會讓共享 controller 與 presenter 更容易重用
- remote connection / control state 不夠通用，不適合放在這一層

目前來源：
- `src/apps/nvda_remote/service.py`
- `src/interop/protocol/routing/message_router.py`
- `src/interop/protocol/session/remote_session.py`

### 5. Process 層級的 bootstrap concern

應抽出：
- logging setup
- config path policy
- runtime factory / composition root helper

原因：
- 這些是跨 app 的啟動責任
- 留在各 app entrypoint 只會持續複製

目前來源：
- `src/apps/nvda_remote/main.py`

## Input Event 契約

這裡提到的「attach listener / handler 的語意」，指的是低階 capture layer 的事件契約，不是 UI callback。

### InputCapture listener 契約

適用於：
- `src/adapters/inputs/base.py` 的 `InputCapture.set_listener(...)`
- `src/application/keyboard.py` 的 `KeyboardInputService.bind()`

目前角色：
- 接收已正規化的 `KeyEvent`
- 讓 app 決定這個按鍵要 suppress 還是 pass through
- 作為低階鍵盤擷取與 app 行為之間的橋接點

目前用途：
- `src/apps/nvda_remote/service.py`
  - 在 controlling 狀態下把按鍵轉送到 remote transport
  - 回傳 `KeyEventDecision.SUPPRESS` 或 `PASS_THROUGH`
- `src/apps/key_echo/service.py`
  - 將按下的鍵轉成本地 speech output
  - 回傳 `KeyEventDecision.SUPPRESS`

建議的共享契約：
- `InputCapture` 一次只接受一個 listener
- `set_listener()` 可在 `start()` 前或執行中呼叫
- 新 listener 會覆蓋舊 listener
- `start()` 要嘛要求先有 listener，要嘛由上層保證在 start 前完成 bind
- key event 以同步方式交給 listener
- listener 回傳 `KeyEventDecision`
- `stop()` 只停止事件來源，不應隱含清掉 listener
- listener 發生失敗時，必須有明確失敗策略，不能讓 hook state 變得不明

### HotkeyCapture handler 契約

適用於：
- `src/adapters/inputs/base.py` 的 `HotkeyCapture.set_handler(...)`

目前角色：
- 接收 hotkey trigger，而不是完整的 `KeyEvent`
- 執行 app 動作，例如切換 control mode

目前用途：
- `src/apps/nvda_remote/service.py`
  - 呼叫 `_handle_hotkey_toggle`

建議的共享契約：
- `HotkeyCapture` 一次只接受一個 handler
- `set_handler()` 可在 `start()` 前或執行中呼叫
- 新 handler 會覆蓋舊 handler
- 當設定好的 hotkey 觸發時，會呼叫 handler
- hotkey 的交付順序與 threading model 應明確記錄
- `stop()` 只停止 hotkey 監聽，不應隱含清掉 handler
- handler 發生失敗時，必須有明確失敗策略，不能讓 hotkey 狀態變得不明

## 目前可留在 App Service

這些內容可以先留在 `NvdaRemoteAppService` 或其他 app service，等到第二個 app 證明有共用需求時再抽。

### 1. App 專屬的使用者流程

可先保留：
- NVDA Remote 專用的 connect / disconnect flow
- start control / stop control 的 UX 行為
- 這個 app 自己的 local stop key 語意
- 作為 remote-control workflow 一部分的 clipboard push command

原因：
- 這些不是通用 input/output capability
- 它們屬於 `nvda_remote` 這個 app 的 use case

### 2. Remote protocol business rule

可先保留：
- controlling 時要送出哪些訊息
- control state 何時算啟用
- `channel_joined`、`version_mismatch` 或 remote status 要如何影響這個 app
- remote 專屬 event，例如：
  - `RemoteConnectionStateChanged`
  - `RemoteControlStateChanged`
  - `RemoteSessionJoined`
  - `RemoteVersionMismatch`

原因：
- 這些規則屬於 remote-control domain
- 其他 app 可能會使用相同 I/O 基礎架構，但完全不碰 relay transport

### 3. 畫面專屬的 controller surface

可先保留：
- 純粹因為 NVDA Remote UI 需要而暴露的方法
- 與特定畫面緊密耦合的 view synchronization 行為

原因：
- 這類內容應該等第二個畫面或第二個 app 真的需要相同形狀時，再考慮抽出

## 判斷清單

在把邏輯從 app service 抽出去之前，先問這幾題：

1. 未來的 app 是否在完全不知道 NVDA Remote 的情況下，也會需要這段行為？
2. 這是在描述可重用 capability，還是只屬於這個 app 的 workflow？
3. 這段程式碼是否明顯提到 transport protocol、control state 或 remote-specific command？
4. 抽出後是否能減少 app entrypoint 之間或未來 app 之間的重複？
5. 抽出後的介面命名，是否可以不提到目前 app 的名稱？

判斷規則：
- 如果第 1、2、4、5 題大多是 yes，就應該抽出去。
- 如果第 3 題是 yes，通常代表它比較適合先留在 app 專屬層。

## 近期重構優先順序

應先做：

1. 從 app entrypoint 抽出共享 bootstrap / provider logic。
2. 穩定可重用的 input/output 介面與 capability 邊界。
3. 以 typed event 取代自由格式的 status dictionary。
   但要注意範圍：共享層只放 capability event，remote domain event 留在 remote 專屬層。

目前不應優先做：

1. 只為了形式漂亮，就把 `NvdaRemoteAppService` 拆成很多小 class。
2. 在第二個 app 還沒出現前，就把 remote-control business rule 硬抽成共享程式碼。

## 實務上的目標狀態

未來新增 app 時，應該可以做到：

- 透過共享 provider 選擇 input capture
- 透過共享 registry 選擇 output capability
- 訂閱 typed 共享 capability event
- 自己建立 app 專屬 workflow，而不需要 import `nvda_remote` 的 service logic

只要能達到這個狀態，即使 `NvdaRemoteAppService` 內部還是偏大，app layer 也已經算夠獨立了。
