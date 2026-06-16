# NVDA Remote Client / Accessibility App Foundation Spec

## 1. 文件目的

這份文件是根據 `docs/superpowers/specs/` 內多份設計文件整理出的「當前最終版本」說明。

重點放在：

- 這個 repository 現在提供哪些功能能力
- 這些能力如何被 `access8graph`、`key_echo`、`nvda_remote` 三個 app 使用
- 為什麼架構會演進成現在的樣子

本文件以功能面與執行行為為主，原始碼資料夾結構只作為輔助說明。

## 2. 產品定位

此專案最早是為了做一個不依賴 NVDA Python runtime 的獨立 NVDA Remote client；後續設計與實作逐步演進後，現在的定位已經更接近：

**一個供 accessibility desktop app 使用的共通 foundation。**

它提供：

- 跨平台鍵盤輸入擷取
- idle / active 模式切換
- app 內事件處理與鍵盤決策模型
- 可切換的語音輸出服務
- 常駐工具型 wxPython app shell
- app-specific 的功能模組承載方式

目前建立在這個 foundation 上的應用有三個：

- `access8graph`
  - 載入 `.graphml` MRT 圖資並以語音導覽圖形的工具 app
- `key_echo`
  - 以最小功能驗證共通輸入與語音輸出能力的 demo app
- `nvda_remote`
  - 連線到 NVDA Remote relay，轉送本地鍵盤事件到遠端，並播放遠端語音輸出

## 3. 核心功能能力

### 3.1 共通輸入能力

專案提供兩種輸入擷取能力：

- `HotkeyCapture`
  - 用於 idle 狀態下的進入熱鍵監聽
- `InputCapture`
  - 用於 active 狀態下的完整鍵盤事件處理

這兩種 capture 不直接承載 app 業務規則。它們的責任是：

- 從平台取得原生鍵盤事件
- 正規化成共通事件模型
- 將事件交給上層 application / app service

### 3.2 HID-first 鍵盤模型

鍵盤共通模型已從早期 Windows `vk/scan/extended` 形式，演進為 **HID-first** 模型。

這個決策的目的很明確：

- 讓 Windows 與 macOS 的平台事件正規化後共用同一套鍵值語意
- 讓 app 層邏輯不再依賴 Windows 專屬鍵盤表示法
- 把舊式 relay payload 相容需求，限制在 `nvda_remote` 的協定邊界內

因此現在的規則是：

- `application`、`apps/*`、mode/hotkey 規則，應以 HID usage 判斷
- 只有 `nvda_remote` 在需要送往既有 relay protocol 時，才會把 HID 事件轉回 legacy key payload

### 3.3 輸入生命週期與 mode 切換

多份 spec 最終收斂出一致的輸入生命週期模型：

- `idle`
  - 只開啟 `HotkeyCapture`
  - 等待進入某個 app mode 的熱鍵
- `active`
  - 關閉 `HotkeyCapture`
  - 啟動 `InputCapture`
  - 由 active keyboard pipeline 處理一般鍵盤事件與退出鍵

這個模型的核心價值是：

- 避免 idle hotkey capture 與 active keyboard capture 重疊
- 讓不同 app 可以共用一致的啟用/退出行為
- 讓 app-specific 規則集中在 mode handler，而不是散落在平台 hook 或 UI

當前的共享行為包含：

- `InputActivationUseCase`
  - 負責 idle / active capture 的互斥切換與失敗回復
- `ModeManager`
  - 管理目前 active mode，並把 key event 路由到該 mode

### 3.4 鍵盤 pipeline 決策模型

專案鍵盤事件處理分為兩個面向：

- 事件要不要送回作業系統
- app 本身有沒有處理該事件

現在的結果模型分成：

- `AppKeyEventResult`
  - 表示 app 內部的 handling 結果
- `KeyboardPipelineResult`
  - 表示最終是否 `send_to_system`

這個設計的重要意義是，它允許這種組合：

- 事件仍送給系統
- app 也執行自己的功能

目前已知的具體情境包括：

- Windows 上 `Num Lock` 需要送給系統保持狀態同步
- `key_echo` 或 `nvda_remote` 仍可能對該事件做自己的 app-side 處理

### 3.5 共通輸出能力

輸出能力的核心是 `SpeechService` 與 `QueuedOutputService`。

`SpeechService` 提供：

- 後端切換
- voice / rate / pitch / volume 控制
- speech sequence 播放

`QueuedOutputService` 提供：

- 面向 app 的較高階輸出入口
- 之後延伸 tone / wave / braille 能力的承接點
- `parallel` / `sequential` 輸出模式

其中 `sequential` / `parallel` 模式的決策，反映了專案對「多次 speak 呼叫」的進一步抽象：

- `parallel`
  - 保留原有行為，新的 speak 可能打斷前一個
- `sequential`
  - 連續 speak 呼叫保證 FIFO 順序

### 3.6 工具型 app shell

在 `key_echo` 與 `access8graph` 的需求推動下，專案建立了可重用的工具型 app shell 概念。

這個平台層的功能重點是：

- 常駐於系統通知區 / menu bar
- 透過共用選單開啟主面板與語音設定
- 關閉主視窗只隱藏，不結束程式
- 將 app-specific 功能裝進可切換的 mode

這使 repo 不再只有「一個 NVDA Remote GUI」，而是能承載多個小型 accessibility 工具 app。

## 4. 三個目前 app 的功能面

### 4.1 `access8graph`

`access8graph` 代表這個 foundation 已從「remote client」擴展到「可訪問工具 app」。

它目前提供的功能包括：

- 從 GUI 選取 `.graphml` 檔案
- 啟動 MRT 圖形導覽
- 將鍵盤命令映射到原始 Access8Graph flow 所需的命令
- 使用共通 speech output 播放車站、路線、選單與導覽內容
- 透過 Escape 或 Stop 按鈕退出導覽模式

它的重要意義有兩層：

- 驗證同一套 foundation 能承載非 remote 類型的 accessibility app
- 證明原本依賴 NVDA runtime 的 app，其核心 flow、模型、輸入與輸出邏輯可以被抽離並重用

### 4.2 `key_echo`

`key_echo` 是用來驗證 foundation 是否真的抽得乾淨的 demo app。

它的目標不是做複雜產品，而是證明：

- 同一套 `InputCapture` / `HotkeyCapture` 可以支援另一個 app
- 同一套 `SpeechService` 可以不依賴 remote 業務邏輯
- mode 啟用、退出、speech settings、tool shell 這些能力可以被重用

它的目前功能行為是：

- idle 時用熱鍵進入 echo mode
- active 時攔截鍵盤事件
- 對 keydown 執行語音回饋
- 在必要情況下仍保留系統 pass-through

`key_echo` 的設計價值比功能本身更重要：它是整個 foundation 共享性的驗證樣本。

### 4.3 `nvda_remote`

`nvda_remote` 仍然是最完整、最接近原始產品目標的 app。

它的主要功能包括：

- 建立 relay transport 與 session
- 連線到既有 NVDA Remote relay
- 進入 control mode 後擷取本地鍵盤
- 將本地 HID key event 轉成既有 remote `key` payload 並送出
- 接收遠端訊息
- 把遠端 `speak` / `cancel` / `pause` 類訊息轉成本地 speech output
- 處理剪貼簿同步

從功能分層看，`nvda_remote` 有兩個特別之處：

- 它同時使用共通 foundation 與 remote protocol/session 能力
- 它是目前唯一仍需要處理 legacy relay 相容邊界的 app

## 5. 目前系統的共通執行流程

### 5.1 啟動流程

每個 app 的 entrypoint 目前都遵循接近一致的 runtime 組裝模式：

1. 透過 `bootstrap.runtime` 初始化 logging / config 路徑政策
2. 透過 `bootstrap.platform` 依平台建立 input/hotkey/clipboard/speech backend options
3. 建立 `OutputScheduler`
4. 建立 `SpeechService`
5. 建立 `QueuedOutputService`
6. 建立 app-specific service
7. 建立 `KeyboardInputService`
8. 建立 wx app / frame / tool shell

這個模式的目的，是把：

- 平台分支
- 程序初始化
- app-specific business wiring

三者分開。

### 5.2 輸入流程

目前標準輸入流程可以整理為：

1. 平台 adapter 擷取原生事件
2. adapter 轉成共通的 `CapturedKeyEvent` 與 HID key event
3. app service 先決定 system pass-through policy
4. `ModeManager` / active handler 執行 app-specific 行為
5. app service 組裝 `KeyboardPipelineResult`
6. adapter 依 `send_to_system` 決定是否 suppress

這個流程的特點是：

- 平台層只關心捕捉與回送系統
- app 層才真正理解該事件的業務意義

### 5.3 輸出流程

目前標準輸出流程為：

1. app 業務邏輯產生語音需求
2. 呼叫 `QueuedOutputService`
3. `QueuedOutputService` 依輸出模式把工作直接送往 `SpeechService`，或先經 shared scheduler 排隊
4. `SpeechService` 使用目前選定 backend 輸出
5. backend 以自己的 scheduler 處理 sequence 內部 chunk

在 `nvda_remote` 中，輸出來源通常是遠端訊息；
在 `key_echo` 與 `access8graph` 中，輸出來源通常是本地互動行為。

## 6. 重要決策脈絡

這些 spec 並不是平行堆疊，而是一條相對清楚的演進路徑。

### 6.1 第一階段：先做獨立 NVDA Remote client

最早的設計重點是：

- 不依賴 NVDA Python runtime
- 在 Windows 上做可運作的 relay client
- 把 transport / session / input / output / UI 分開

這個階段的核心成果是確立了「協定與平台 adapter 分離」的方向。

### 6.2 第二階段：把輸入與輸出從 remote 業務抽離

當 `key_echo` 被提出後，專案不再只是 remote client。

關鍵決策變成：

- input 不是 remote 專屬能力
- output 不是 remote 專屬能力
- app service 才是唯一理解業務規則的地方

這一步讓 `SpeechService`、`KeyboardInputService`、`OutputCapabilities` 這些共享能力開始成形。

### 6.3 第三階段：把重複的 app 啟動與平台邏輯抽成 foundation

當兩個 app 已經存在後，重複的 platform / runtime wiring 變成明顯負擔，因此有了：

- `bootstrap.platform`
- `bootstrap.runtime`

這表示專案正式承認自己不只是一個單 app 程式，而是一個多 app codebase。

### 6.4 第四階段：統一 app 層模式與輸入生命週期

接著 spec 把注意力放到 app 層結構與 mode 問題：

- facade + focused use case
- idle hotkey / active keyboard
- `InputActivationUseCase`
- `ModeManager`

這一步的重要成果，是讓 app 不再各自發明自己的輸入切換規則。

### 6.5 第五階段：把鍵盤模型從 Windows 語意拉回平台中立

在 Windows 與 macOS 都開始存在後，早期 `vk/scan/extended` 模型的侷限變得明顯，因此決定改成 HID-first。

這是整個 codebase 從「Windows 為核心」轉向「平台中立 foundation」的關鍵一步。

### 6.6 第六階段：從兩個 app 擴展到工具平台

當 `key_echo` 之外又需要 `access8graph` 這類工具時，tray/tool app platform 的價值浮現：

- 共同 shell
- 共同 speech settings
- mode-based activation
- app-specific panel

此時 repo 的最終形狀，已經不是「remote client + demo」，而是「remote client + demo + migration target app」共用同一個 foundation。

## 7. 當前最終結論

綜合所有歷史 spec，可以把目前這個 repository 的最終形態定義為：

**一個以 HID-first 輸入模型、共享語音輸出服務、mode-based 事件處理、tray/tool app shell 與 app-specific orchestration 為核心的 accessibility desktop app foundation。**

它目前已經成功承載三種不同性質的 app：

- remote control client
- local key echo demo
- graph-based spoken navigation tool

這代表當初從 `nvda_remote` 出發的設計，最終已經發展成一套可以支援多種 accessibility 桌面工具的共享基礎架構。

## 8. 目前原始碼對應關係

原始碼目錄不是本文件主軸，但為了方便對照，現在的責任大致如下：

- `src/adapters/`
  - 平台專屬輸入/輸出實作
- `src/application/`
  - 共通輸入、輸出、keyboard pipeline、speech service
- `src/bootstrap/`
  - 平台 factory 與程序級初始化
- `src/interop/`
  - key、speech、protocol、transport 等共享模型與互通邊界
- `src/apps/`
  - `access8graph`、`key_echo`、`nvda_remote` 的 app-specific orchestration
- `src/apps/shared/`
  - 可重用的 mode / tool shell / speech settings controller
- `src/ui/`
  - wxPython UI 與 app-specific frame

若從功能角度理解，最重要的邊界不是資料夾名稱，而是：

- 平台能力在 `adapters`
- 共通流程在 `application` / `bootstrap`
- app-specific 行為在 `apps/*`
- 對外協定與共享模型在 `interop`
