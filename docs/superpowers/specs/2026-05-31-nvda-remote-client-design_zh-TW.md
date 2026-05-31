# NVDA Remote Client 設計文件

## 概述

本文件定義一個獨立運作的 NVDA Remote Windows client 第一版實作。此 client 會連線到既有的 NVDA Remote relay endpoint，並控制另一台已經啟用 NVDA Remote 的電腦。新的 client 必須在不依賴 NVDA Python runtime 的情況下運作，並將輸入、輸出、控制與平台相關職責模組化，以便後續擴充到其他平台。

第一版目標平台為 Windows，應用程式與核心邏輯使用 Python 開發。UI 使用 `wxPython` 建構。當本機有執行 NVDA 時，可利用 `nvdaControllerClient64.dll` 提供本機語音輸出；但即使本機未執行 NVDA，整個應用程式仍必須可以正常運作。

## 目標

- 建立一個可獨立運作的 client，能連線到 NVDA Remote relay 並以控制端身分加入 channel。
- 在 Windows 上支援真正的鍵盤擷取，並將鍵盤事件轉送到遠端電腦。
- 接收遠端語音輸出，並透過模組化輸出管線在本機呈現。
- 支援雙向剪貼簿同步。
- 保持 protocol、session、transport、input、output 與 UI 的責任分離。
- 避免在新應用程式核心中依賴 NVDA 的 Python runtime API。

## V1 不包含的範圍

- 實作 follower 模式，讓其他電腦控制本機 client。
- 實作完整的點字輸出支援。
- 實作可正式使用等級的 tone 與 wave 播放。
- 實作 secure desktop 處理與完整 SAS 支援。
- 實作 URL handler 整合。
- 實作完整 NVDA script 與點字手勢相容性。
- 支援在 client 內啟動本地 relay server。
- 提供非 Windows 平台的 adapter 實作。

## 建議架構

建議採用分層式 Python 應用程式架構，明確區分純 client 邏輯與 Windows 專用 adapter。

### 分層

#### `remote_core`

純 client 邏輯，不直接依賴 `wxPython`、Win32 hook、剪貼簿 API 或 NVDA controller DLL。

職責：

- Protocol 定義
- 序列化與反序列化
- Transport 抽象與 relay 連線處理
- Session 狀態與連線生命週期
- Message routing
- 正規化輸入與輸出事件的 domain model

#### `application`

負責協調 UI、core 與 adapters 的應用程式服務層。

職責：

- `connect`、`disconnect`、`start control`、`pause control`、`clipboard push` 等高階 use case
- 對 UI 暴露的 runtime state
- core 與 UI 之間的事件傳遞
- 相依元件組裝

#### `adapters`

位於穩定介面後方的平台或裝置專用實作。

Windows v1 adapter 包含：

- 鍵盤擷取
- 剪貼簿存取
- 可選的鍵盤注入輔助元件
- NVDA controller DLL 語音輸出
- 對不支援輸出的 logging 或 null 實作

#### `app_wx`

以 `wxPython` 建構的薄 GUI shell。

職責：

- 主視窗與對話框
- 使用者觸發的操作
- 顯示連線狀態與錯誤
- 提供本機使用者回饋的狀態訊息

GUI 不應擁有 transport 邏輯或 protocol 邏輯。

## 核心 Runtime 模型

V1 應保留連線角色的概念，但不直接複製 NVDA 目前的物件模型。內部資料模型應保留 `mode` 欄位以便未來擴充，但 Windows v1 UI 不需暴露角色選擇。V1 固定以控制端模式運作。

### 主要 Runtime 物件

#### `ClientRuntime`

執行中應用程式的頂層協調者。

職責：

- 持有 transport、session、adapters 與 application state 的參考
- 啟用與停用控制模式
- 在 input capture、transport 與 output services 之間路由正規化事件

#### `RemoteSession`

代表一個存活中的 relay session，並擁有 session 生命週期狀態。

職責：

- 加入 relay channel
- 驗證 protocol version 相容性
- 追蹤連線狀態
- 處理 ping、disconnect、MOTD 與 join/leave 事件

#### `MessageRouter`

接收解碼後的 protocol message，並分派到對應的 domain handler。

職責：

- 將 message type 映射到 handler
- 將輸入中的輸出相關 message 轉換成正規化 output request
- 保持 routing 邏輯獨立於 GUI 與平台 API

#### `ControlState`

輸入轉送的狀態機：

- `idle`
- `connected`
- `controlling`
- `suspended`

意義：

- `idle`：未連線
- `connected`：已連到 relay，但鍵盤擷取尚未轉送輸入
- `controlling`：鍵盤擷取已啟用，且會送出 outbound key message
- `suspended`：transport 仍維持連線，但控制轉送已暫停

需要這個切分，才能讓使用者在保持連線的情況下，不必一直把本機鍵盤交給遠端。

## 訊息與資料流

### 連線流程

1. GUI 收集 `host`、`port` 與 `key`。
2. Application 以內部固定為控制端行為的 mode 建立 connection information。
3. Transport 與 relay 建立 TCP/TLS 連線。
4. Session 完成 protocol negotiation 與 channel join。
5. Runtime state 轉為 `connected`。

### 控制流程

1. 使用者從 GUI 啟動控制。
2. Application 啟用 Windows 鍵盤擷取 adapter。
3. 擷取到的按鍵事件會正規化為平台無關的 `KeyEvent` 物件。
4. `remote_core` 將 `KeyEvent` 物件映射成 NVDA Remote `KEY` message。
5. Transport 將編碼後的 message 送到 relay。

這樣可以把擷取邏輯與 protocol 編碼邏輯分離。未來若支援其他平台，只要能產生相同的正規化 `KeyEvent` model，理論上只需要新的 capture adapter。

### 輸出流程

1. Transport 收到 message。
2. Serializer 解碼 payload。
3. `MessageRouter` 依 protocol type 進行分派。
4. 與輸出相關的 handler 建立正規化 output request。
5. `OutputManager` 將這些 request 轉送到對應的 output adapter。

GUI 只應接收來自 application layer 的狀態事件，不應直接消費原始 transport message。

## 輸入設計

V1 需要在 Windows 上支援真正的鍵盤擷取。僅靠指令式或文字主控台控制模型並不足夠。

### 輸入抽象

定義 `InputCapture` 介面，至少提供下列操作：

- `start()`
- `stop()`
- `set_listener(listener)`

Listener 會接收正規化的 `KeyEvent` 物件，至少包含：

- virtual key code
- 可取得時的 scan code
- 是否為 extended key
- 按下或放開狀態

### Windows V1 輸入 Adapter

以 Windows 專用 adapter 方式實作 `WindowsKeyboardCapture`。

職責：

- 安裝與移除 keyboard hook
- 正規化擷取到的事件
- 避免在 hook 層中嵌入 NVDA Remote protocol 細節

Keyboard hook 必須位於 `remote_core` 之外。

## 輸出設計

輸出處理必須模組化，且不得要求本機一定要執行 NVDA。

### `OutputManager`

面向 application 的中央輸出協調者。

職責：

- 接收來自 `MessageRouter` 的正規化 output request
- 分派給正確的 output service
- 當特定 output backend 無法使用時，提供可優雅退化的行為

### 輸出介面

#### `SpeechOutput`

操作：

- `speak(payload)`
- `cancel()`
- `pause(is_paused)`

#### `BrailleOutput`

保留給未來支援的介面。V1 應提供 null implementation。

#### `ToneOutput`

保留給未來支援的介面。V1 應提供 logging implementation。

#### `WaveOutput`

保留給未來支援的介面。V1 應提供 logging implementation。

#### `ClipboardService`

操作：

- `set_text(text)`
- `get_text()`

## 語音相容策略

語音是輸出面風險最高的區域，因為 NVDA Remote 目前會序列化 NVDA 專屬的 speech command 物件。新的 client core 不應直接依賴 NVDA runtime internals 來解讀這些物件。

### 正規化需求

輸入的 speech 資料在進入 output adapter 之前，必須先轉換成中介模型。

定義 `NormalizedSpeech` model，包含：

- `segments: list[SpeechSegment]`

V1 的 `SpeechSegment` 類型：

- `text`
- `break`
- 可選的 prosody hint，例如 pitch change；即使 backend 忽略，也可先保留其結構

這個中介模型會成為 `remote_core` 與 speech backend 之間的契約。

### Windows V1 語音 Backend

實作 `NvdaControllerSpeechOutput`。

行為：

- 當本機可使用 NVDA 時，透過 `nvdaControllerClient64.dll` 以本機 NVDA 呈現正規化後的語音內容。
- 當本機無法使用 NVDA 時，必須優雅退化，不能破壞 client runtime。
- 在有幫助的情況下，可將狀態資訊回報給 GUI，但不可讓本機 NVDA 成為連線或控制流程的硬性依賴。

DLL 整合屬於 adapter 職責。`remote_core` 不應知道語音實際如何被唸出。

## 剪貼簿同步

剪貼簿同步屬於 V1 範圍。

### 輸入方向剪貼簿

- 接收 `SET_CLIPBOARD_TEXT`
- 經由 `MessageRouter`
- 呼叫 `ClipboardService.set_text(text)`

### 輸出方向剪貼簿

- 在 GUI 或選單中提供將本機剪貼簿推送到遠端 session 的使用者操作
- 透過 `ClipboardService.get_text()` 讀取本機剪貼簿文字
- 經由 transport 送出 `SET_CLIPBOARD_TEXT`

剪貼簿邏輯應和其他輸出一樣，遵循 message-to-adapter pipeline，而不是直接放在 GUI 程式碼中。

## Windows V1 功能範圍

### 包含

- 連線到既有的 NVDA Remote relay endpoint
- 使用 host、port 與 key 加入 channel
- 以控制端模式運作
- 提供 `wxPython` GUI 進行連線管理與控制切換
- 透過 Windows 鍵盤擷取進行遠端控制
- 接收遠端 speech，並透過 output pipeline 處理
- 支援雙向剪貼簿同步
- Session 事件：protocol mismatch、join/leave、ping、disconnect 與 MOTD
- 提供 braille、tone 與 wave 的 stub 或 logging output implementation

### 不包含

- Follower mode
- 完整點字呈現
- 正式等級的 tone 與 wave 播放
- Secure desktop 與完整 SAS 工作流程
- 本地 relay hosting
- 跨平台 adapter 實作

## 錯誤處理與退化行為

Runtime 應將大多數平台層失敗視為功能退化，而不是致命錯誤。

範例：

- Relay 連線失敗會阻止 session 啟動，且必須在 GUI 中明確顯示。
- Keyboard hook 啟動失敗會阻止 control mode，且必須清楚回報。
- 本機無法使用 NVDA 做語音輸出時，不應終止整個 session。
- 不支援的 speech command 細節應盡量退化為可用的正規化表示，而不是讓 router 當掉。
- 剪貼簿存取失敗應對該次操作提供使用者可見的錯誤，但不應終止 transport session。

## 並行模型

Windows UI、network I/O 與 keyboard capture 必須保持分離。

指引：

- Transport 與 socket I/O 不可阻塞 `wxPython` UI thread。
- Keyboard hook 處理不可直接跑在 UI thread 上。
- 在狀態變更與使用者可見通知進入 GUI 前，應先經過 application layer。
- 避免從 transport 或 hook callback 直接呼叫 GUI。

實際 thread 與 event-loop 的細節可以在 implementation planning 階段決定，但分層限制不可破壞。

## 測試策略

V1 應包含三層驗證。

### 單元測試

- Protocol 編碼與解碼
- 依 message type 的 routing 行為
- Speech 正規化行為
- Clipboard service 契約行為

### 整合測試

- 連線到 relay server
- 加入 channel
- 交換 `KEY`、`SPEAK`、`SET_CLIPBOARD_TEXT` 與 `PING`
- 驗證 disconnect 與 protocol mismatch 處理

### Windows 手動測試

- GUI 連線流程
- 啟動與暫停 control mode
- 基本按鍵轉送，包括導覽鍵與輸入鍵
- 本機有執行 NVDA 與未執行 NVDA 兩種情境
- 雙向剪貼簿同步
- 重新連線與中斷連線行為

## 建議專案結構

```text
nvda_remote_client/
  src/
    app_wx/
      main.py
      app.py
      main_frame.py
      dialogs/
    application/
      services.py
      controller.py
      state.py
      events.py
    remote_core/
      protocol.py
      serializer.py
      connection_info.py
      transport/
      session/
      routing/
      models/
    adapters/
      windows/
        keyboard_hook.py
        keyboard_sender.py
        clipboard.py
        nvda_controller.py
      outputs/
        speech.py
        braille.py
        tone.py
        wave.py
      inputs/
        base.py
    tests/
      unit/
      integration/
  docs/
    superpowers/
      specs/
```

實際檔名可在 implementation planning 階段再調整，但高層責任分離必須保留。

## 刻意延後到 Planning 階段的開放決策

以下項目刻意留到 implementation planning，而不是因為目前未知，而是因為它們取決於實際驗證或封裝限制：

- Windows 上 keyboard hook 的具體實作細節
- Worker thread 與 `wxPython` 之間的事件橋接機制
- 封裝與發佈格式
- 是否在 v1 中額外提供第二套 speech backend，例如 Windows SAPI，作為可選 fallback

這些屬於執行細節，不是未決的產品範圍。

## 最終建議

將此 client 建構為分層式 Python 應用程式，包含：

- `remote_core`：負責 protocol、session 與 routing
- `application`：負責 use-case 協調與 state
- Windows adapters：負責 input、clipboard 與可選的 NVDA 語音輸出
- `wxPython`：作為薄 GUI shell

V1 應交付一個可在 Windows 上實際使用的控制端 client，同時維持良好的模組邊界，以保留未來可攜性。必要功能目標是鍵盤控制、透過正規化管線處理遠端語音，以及雙向剪貼簿同步；braille、tone 與 wave 則先保留為擴充點，而不是完整功能。
