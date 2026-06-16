# accessibility-toolkit 架構規格

## 1. 文件目的

這份文件說明 `accessibility-toolkit` 目前的系統架構。

它是寫給新加入的協作者與開發者，幫助理解：

- toolkit 負責哪些事情
- 哪些內容屬於共享層，哪些屬於 app 專屬層
- 現有參考 app 如何使用這個 toolkit
- 為什麼架構會演進成現在這個樣子

這是一份架構與系統脈絡文件，不是主要 onboarding 文件，也不是產品需求文件。

## 2. 系統定位

`accessibility-toolkit` 是一套供無障礙桌面應用使用的共享執行期。

它的核心架構職責包括：

- 在支援的平台上擷取鍵盤與快速鍵輸入
- 將輸入正規化成共享模型
- 管理模式切換與互動控制
- 透過共享模型鍵盤事件處理管線路由事件
- 提供可重複使用的語音與輸出排程服務
- 提供可重複使用的應用程式介面行為

目前這個 toolkit 由三個參考 app 實際使用：

- `access8graph`
- `key_echo`
- `nvda_remote`

## 3. Toolkit 核心能力

### 3.1 鍵盤與快速鍵擷取

toolkit 提供兩種 capture 概念：

- `HotkeyCapture`
  - 用在 app 閒置、等待進入 mode 的狀態
- `InputCapture`
  - 用在 app 啟用後、處理完整鍵盤輸入的狀態

平台 adapter 的責任是擷取原生事件並轉成共享事件模型，不應在 adapter 層就混入業務語意。

### 3.2 HID-First 輸入模型

toolkit 以 HID-first 作為鍵盤識別的共享模型。

這個決策的重要性在於：

- 共享 app 邏輯不再依賴 Windows 專屬的 `vk/scan/extended`
- Windows 與 macOS 可以共用同一套 app 層規則
- 舊版協定相容需求被隔離在真正需要它的邊界

目前規則是：

- 共享層與 app 邏輯應該以 HID usage 推論鍵盤語意
- 只有 `nvda_remote` 會把 HID 輸入轉回 legacy relay key payload

### 3.3 模式切換與互動控制

toolkit 使用共享的生命週期模型：

- `idle`
  - `HotkeyCapture` 啟用
  - app 等待進入 mode 的熱鍵
- `active`
  - `InputCapture` 啟用
  - app 處理一般按鍵事件與退出行為

這套生命週期由共享邏輯協調，避免每個 app 自己重新發明 capture 切換規則與互動控制流程。

核心共享元件：

- `InputActivationUseCase`
  - 負責 capture 切換與失敗回復
- `ModeManager`
  - 負責目前 active mode 與 active 事件路由

### 3.4 鍵盤事件處理管線

toolkit 將兩件原本混在一起的事情拆開：

- 事件要不要送回作業系統
- app 是否有處理該事件

目前的結果模型：

- `AppKeyEventResult`
  - app 內部 handling 語意
- `KeyboardPipelineResult`
  - 面向系統邊界的最終結果，包含 `send_to_system`

這讓 toolkit 可以表達這種合法組合：

- 系統仍收到該按鍵
- app 也執行自己的本地行為

例如 Windows 上的 `Num Lock`。

### 3.5 語音與輸出排程

toolkit 提供：

- `SpeechService`
  - 後端選擇
  - voice/rate/pitch/volume 設定
  - speech sequence 播放
- `QueuedOutputService`
  - 較高階的輸出入口
  - 輸出順序控制
  - 未來擴充非語音輸出的承接點

這套共享輸出模型，讓 app 可以提供語音回饋，而不必在每個 app 裡重寫 backend 專屬邏輯。

### 3.6 應用程式介面

toolkit 內含可重複使用的 wxPython 桌面工具型應用程式介面。

它支援：

- tray 或 menu-bar 型 app 存在方式
- 主面板生命週期
- 語音設定面板入口
- 工具型 app 的關閉即隱藏行為

這也是 `key_echo` 與 `access8graph` 會被感知為同一套工具，而不是兩個完全獨立殼層的重要原因。

## 4. Toolkit 邊界

這是整個 repository 最重要的架構邊界。

### 4.1 哪些屬於 Toolkit

toolkit 負責：

- 平台輸入／輸出 adapter
- 共享輸入正規化與 capture 契約
- 模式切換與互動控制規則
- 鍵盤事件處理管線
- 語音與輸出排程服務
- 共享 bootstrap / runtime wiring
- 可重用的應用程式介面行為

### 4.2 哪些不屬於 Toolkit

toolkit 不負責：

- NVDA Remote 的 session 語意
- remote relay 訊息處理規則
- 圖形導覽業務規則
- app 專屬使用者流程
- app 專屬驗證或 domain state

這些都應該留在各 app 自己的 module 與 service 中。

### 4.3 這個邊界為什麼重要

如果沒有這個邊界：

- 平台細節會滲進 app 行為
- app 專屬規則會硬化成假的「共享抽象」
- 新增 app 的成本會提高，因為共享層不再可信

這套架構的刻意設計，就是要讓共享 toolkit 保持可重用，同時讓 app 本身能夠維持有意義的差異。

## 5. 參考 App 與它們的角色

### 5.1 `access8graph`

角色：

- 驗證 toolkit 可以承載非 remote 類型的無障礙工具

app 專屬職責：

- GraphML 載入
- MRT 模型建立
- 導覽命令與語音圖形探索

app 使用到的 toolkit 職責：

- 輸入啟用
- 鍵盤事件處理管線
- 語音與輸出排程
- 應用程式介面與語音設定 UI

### 5.2 `key_echo`

角色：

- 驗證 toolkit 的共享輸入與語音基礎設施可以支援一個最小的本地 app

app 專屬職責：

- echo mode 行為
- keydown 到語音輸出的映射

app 使用到的 toolkit 職責：

- capture 生命週期
- 鍵盤事件處理管線
- 語音後端管理
- 應用程式介面行為

### 5.3 `nvda_remote`

角色：

- 提供這個專案最初想解決的 remote-control 使用情境

app 專屬職責：

- relay transport 與 session 處理
- 遠端按鍵轉送規則
- 遠端語音訊息處理
- 剪貼簿同步行為

app 使用到的 toolkit 職責：

- 共享輸入模型
- 共享輸出模型
- 語音後端管理
- runtime / bootstrap wiring

特殊之處：

- `nvda_remote` 是目前唯一仍需要 legacy relay 相容邊界的 app

## 6. 共享執行流程

### 6.1 啟動流程

每個 app 目前都遵循接近一致的 runtime 形狀：

1. 初始化 logging 與 runtime 路徑
2. 解析平台專屬 adapter 與 backend options
3. 建立 output scheduler 與 speech service
4. 建立 queued output service
5. 建立 app 專屬 service
6. 建立 keyboard input service
7. 建立 wx app / interface / frame

這樣可以把平台政策、runtime 政策與 app 專屬 wiring 分開。

### 6.2 輸入流程

共享輸入流程：

1. 平台 adapter 擷取原生事件
2. adapter 發出共享 key event 結構
3. app service 評估 system pass-through policy
4. mode manager 或 active handler 執行 app 邏輯
5. app service 組裝 `KeyboardPipelineResult`
6. adapter 決定 suppress 或 pass through

### 6.3 輸出流程

共享輸出流程：

1. app 行為產生語音／輸出需求
2. 需求進入 `QueuedOutputService`
3. queued service 依 output mode 直接路由或排隊
4. `SpeechService` 使用目前選定的 backend
5. backend scheduler 處理 sequence 內部 chunk

## 7. 設計演進脈絡

這個 repository 並不是一開始就以 general toolkit 為目標。現在的架構，是多個具體壓力點推動的結果。

### 7.1 獨立的 NVDA Remote Client

最初目標：

- 建立一個不依賴 NVDA Python runtime internals 的 NVDA Remote client

架構結果：

- 協定與平台 concerns 從一開始就分開

### 7.2 共享輸入／輸出抽取

壓力來源：

- `key_echo` 證明輸入與輸出不應該仍然是 remote 專屬能力

架構結果：

- speech、keyboard input 與 output capability 層變成共享服務

### 7.3 共享 Bootstrap

壓力來源：

- 多個 app 暴露出重複的啟動、平台解析與 runtime policy 程式碼

架構結果：

- `bootstrap.platform` 與 `bootstrap.runtime` 集中管理共享 runtime wiring

### 7.4 統一 Mode 生命週期

壓力來源：

- 不同 app 在如何進入與退出 active keyboard handling 上開始產生漂移

架構結果：

- 共享 activation use case 與 mode 管理變成第一級概念

### 7.5 HID-First 模型

壓力來源：

- 以 Windows 為中心的鍵盤語意不是長期穩定的核心模型

架構結果：

- 共享邏輯轉向 HID-first 鍵盤識別

### 7.6 應用程式介面平台

壓力來源：

- `access8graph` 與 `key_echo` 需要可重複使用的應用程式介面行為

架構結果：

- repository 從單一 client 加附屬功能，演進成可承載多個無障礙桌面 app 的 toolkit

## 8. 目前原始碼對應

架構與原始碼的對應大致如下：

- `src/adapters/`
  - 平台專屬實作
- `src/application/`
  - 共用輸入、輸出、鍵盤與語音行為
- `src/bootstrap/`
  - 共享 runtime / bootstrap wiring
- `src/interop/`
  - 共享協定、transport、key 與 speech 模型
- `src/apps/`
  - app 專屬組裝
- `src/apps/shared/`
  - 可重用的介面、mode 與 controller helper
- `src/ui/`
  - wxPython UI

真正重要的不是資料夾名稱本身，而是這個原則：共享 runtime 行為留在共享層，domain 行為留在擁有它的 app。
