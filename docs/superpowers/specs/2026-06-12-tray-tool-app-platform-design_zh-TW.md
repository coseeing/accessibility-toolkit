# Tray Tool App Platform 設計

## 目的

為 `nvda_remote`、`key_echo` 與未來新增的小工具 app 建立一個可重用的 app 平台，讓新 app 可以共用：

- 常駐系統通知區圖示啟動模型
- 共用圖示選單
- 主面板與語音設定面板生命週期
- 多組 active/inactive mode 的輸入切換模型
- 語音設定控制邏輯

本階段的目標不是為了套用更多 design patterns，也不是把現有架構全面 generic 化。目標是根據下一階段需求，將目前已經重複出現的 app shell 與 mode 行為收斂成可重用的骨架，降低新增第三個、第四個工具 app 的成本。

## 背景

目前專案已具備以下可重用基礎：

- `Transport`、`SpeechOutput`、`InputCapture` 等 protocol 邊界
- `InputActivationUseCase` 的 active/inactive capture 切換
- `ActiveKeyEventPolicy` 的 active 狀態按鍵路由
- `KeyEchoAppFacade` 與 `NvdaRemoteAppFacade` 的 facade + use case 組合模式

但目前也存在明確的結構問題：

- app facade 同時承擔 lifecycle、input orchestration、status dispatch、speech settings proxy
- `key_echo` 與 `nvda_remote` 共享的 app shell 行為尚未抽出
- speech settings use case 在兩個 app 間幾乎重複
- UI 仍是以直接開啟視窗為中心，尚未轉成系統通知區圖示常駐模型
- 同一 app 內若未來需要多個 active/inactive 功能，目前沒有明確的 mode 模型承接

## 下一階段需求摘要

未來工具 app 需要支援以下共用行為：

1. 以 hotkey 進入完整鍵盤攔截模式，並在 active 狀態下以另一個或相同 hotkey 離開。
2. 單一 app 內可能有多組這樣的功能，每組有自己的 enter/exit hotkey 與 active keyboard behavior。
3. app 啟動後常駐於系統通知區圖示；在 Windows 為 tray icon，在 macOS 為 menu bar status item。使用者透過圖示選單開啟主面板、語音設定，或結束程式。
4. 關閉主面板只隱藏視窗，不退出整個程式；真正退出需走圖示選單中的「結束」。
5. 語音設定需獨立為共用面板，由圖示選單開啟。

需求參考來源包含 NVDA 目前的 `wx.App + 隱藏 MainFrame + TaskBarIcon` 模型。

## Design Patterns vs SOLID Review

### 已經做對的部分

- 以 `Protocol` 作為 ports，符合 dependency inversion。
- app 層以 facade 協調 use cases，而不是讓 UI 直接碰 transport 或 adapters。
- `SpeechBackendManager` 已實際扮演 strategy selector，這是有實際變化點支撐的 pattern。

### 目前真正的問題

- `NvdaRemoteAppFacade` 與 `KeyEchoAppFacade` 已開始同時承擔太多責任，`SRP` 壓力明顯。
- 兩個 app 在 lifecycle、speech settings、status listener、capture bind 上有重複結構，但尚未形成穩定共用層。
- `RuntimeState` 與 `nvda_remote` 的 remote/session 流程不適合直接作為所有工具 app 的通用 state 核心。

### 本階段不建議的方向

- 不先引入大型 event bus 或 mediator。
- 不先建立肥大的 `BaseAppFacade` 繼承階層。
- 不先把 remote session/protocol generic 化到所有工具 app。

原因很直接：這些做法會讓架構看起來更 pattern-heavy，但沒有直接服務目前的擴張需求，屬於 overlay design。

## 設計目標

1. 讓新增一個小工具 app 時，不需要再重做一份通知區圖示 shell、panel、speech settings、input activation 骨架。
2. 讓單一 app 可以註冊多個 mode，每個 mode 自帶自己的進入/退出 hotkey 與 active keyboard behavior。
3. 將共用 shell 與 app-specific business behavior 明確分界。
4. 保留 `nvda_remote` 的 remote/session 特例，不強迫所有工具 app 依附其狀態模型。
5. 讓 `key_echo` 與未來新工具 app 先享受到平台收益，再逐步讓 `nvda_remote` 接入可共用的部分。

## 非目標

- 重新設計整個 protocol、relay、session 架構
- 動態載入 plugin 或 app
- 支援可編輯的 hotkey 設定 UI
- 將所有 app 狀態流改寫為 typed events
- 合併所有 app 成單一 mega-app

## 推薦方案

採用 **Tray Tool App Platform**。

核心想法是把目前重複出現的結構拆成四個穩定邊界：

1. `TrayAppShell`
2. `ModeManager`
3. `PanelController`
4. `SpeechSettingsController`

每個 app 保留自己的業務 use case，只向平台註冊：

- app metadata
- 主面板
- mode 列表
- 額外 menu items（若需要）

## 架構總覽

```text
wx.App
  -> TrayAppShell
       -> TaskBarIcon / status item menu
       -> PanelController
       -> SpeechSettingsController
       -> ModeManager
            -> ActivationMode A
            -> ActivationMode B
            -> ActivationMode C
       -> App-specific facade / use cases
```

平台層負責「如何運行一個常駐工具 app」。

app 層負責「這個 app 的 mode 做什麼事」。

## 核心元件

### TrayAppShell

責任：

- 啟動 `wx.App`
- 建立跨平台 `TaskBarIcon`
- 管理共用圖示選單
- 管理 app 退出流程
- 與 `PanelController` 協調面板顯示/隱藏
- 與 `ModeManager` 協調啟動時的 mode 綁定

固定共用圖示選單：

- 主面板
- 語音設定
- 結束

非責任：

- app-specific business logic
- remote protocol/session
- active mode 內部的 key handling 規則

### PanelController

責任：

- 建立與註冊主面板、語音設定面板
- 統一處理 show / hide / focus / restore
- 攔截視窗關閉事件並改為隱藏
- 提供圖示選單開啟面板的統一入口

設計要求：

- 主面板關閉時只 `Hide()`，不退出 app
- 語音設定面板關閉時也只隱藏
- 真正的 app 結束由 `TrayAppShell` 統一處理

### SpeechSettingsController

責任：

- 封裝 `SpeechOutputService` 的 backend/voice/rate/pitch/volume 操作
- 提供語音設定面板需要的查詢與修改介面
- 可選擇性支援 backend changed callback

這個元件將取代目前重複的：

- `src/apps/nvda_remote/use_cases/speech_settings.py`
- `src/apps/key_echo/use_cases/speech_settings.py`

### ActivationMode

`ActivationMode` 代表 app 內一組可啟用的功能。

每個 mode 至少需要定義：

- `mode_id`
- `enter_hotkey`
- `exit_hotkey`
- `can_enter() -> bool`
- `enter() -> bool`
- `exit() -> bool`
- `handle_key_event(event) -> KeyEventDecision`

說明：

- `enter_hotkey` 用於 idle 狀態下從 `HotkeyCapture` 進入 active
- `exit_hotkey` 用於 active 狀態下從 `InputCapture` 離開 active
- `handle_key_event` 定義 active 狀態下其餘按鍵行為

### ModeManager

責任：

- 註冊多個 `ActivationMode`
- 監聽 idle 狀態下的 mode 啟動 hotkey
- 保證同一時間只有一個 active mode
- 在 `HotkeyCapture` 與 `InputCapture` 間切換
- 將鍵盤事件路由到目前 active mode
- 發出 mode 狀態通知供 UI 或圖示選單顯示

### 跨平台圖示行為

本設計中的 `TaskBarIcon` 應被視為跨平台系統通知區圖示抽象：

- Windows: notification area / tray icon
- macOS: menu bar status item

實作要求：

- 不將互動模型硬編碼為 Windows 的右鍵 tray 行為
- 選單顯示應優先以 `wx.adv.TaskBarIcon` 的 `CreatePopupMenu()` 或 `GetPopupMenu()` 為中心
- 不假設所有平台都完整支援相同的滑鼠事件或 `PopupMenu()` 行為

這樣可以避免 Cocoa port 下的事件差異污染平台設計。

`ModeManager` 不應知道：

- remote session 的存在
- speech echo 的具體商業規則
- app 各面板如何布局

### ModeActivationCoordinator

這層可由現有 `InputActivationUseCase` 演進而來。

責任：

- 切換 active/inactive capture ownership
- 維持 `HotkeyCapture` 與 `InputCapture` 互斥
- 在切換失敗時進行恢復

與現狀的差異：

- 現在只表達「是否 active」
- 下一階段需表達「哪個 mode active」

### ActiveKeyEventPolicy

現有 `ActiveKeyEventPolicy` 的概念可以保留，但不應再固定綁單一 app。

建議演進方向：

- exit key 來自目前 active mode
- 非 exit key 由 active mode 的 `handle_key_event()` 處理
- policy 只管路由，不管業務規則

## App 邊界

### 適合進平台層的內容

- 系統通知區圖示與共用圖示選單
- 主面板與語音設定面板的 show/hide lifecycle
- speech settings controller
- active/inactive capture 切換
- mode registry 與 mode 路由
- 共用 status notifier

### 應留在 app-specific 層的內容

- `nvda_remote` 的 `RemoteSession`
- `nvda_remote` 的 `MessageRouter`
- remote key forwarding 與 clipboard 規則
- `key_echo` 的 echo 語音內容規則
- 各 app 主面板的內容與特定操作

## 檔案與模組建議

建議新增共用 app platform 區：

```text
src/apps/shared/
  tool_app_shell.py
  panel_controller.py
  speech_settings_controller.py
  mode_manager.py
  mode_types.py
  tray_icon.py
```

可能的職責拆分：

- `tool_app_shell.py`
  - app 啟動、退出、menu wiring
- `panel_controller.py`
  - 主面板/語音設定面板 show-hide 管理
- `speech_settings_controller.py`
  - 共用語音設定查詢與更新
- `mode_manager.py`
  - mode 註冊、hotkey 啟動、active key 路由
- `mode_types.py`
  - `ActivationMode` protocol 或 dataclass
- `tray_icon.py`
  - 跨平台 wx `TaskBarIcon` wrapper

## 與現有檔案的關係

### 優先收斂的現有檔案

- `src/apps/nvda_remote/use_cases/speech_settings.py`
- `src/apps/key_echo/use_cases/speech_settings.py`
- `src/application/input/activation.py`
- `src/application/input/active_key_policy.py`
- `src/ui/nvda_remote/app.py`
- `src/ui/echo/app.py`

### 先不要抽成共用平台的現有檔案

- `src/apps/nvda_remote/facade.py`
- `src/interop/protocol/session/remote_session.py`
- `src/interop/protocol/routing/message_router.py`
- `src/application/state.py`

理由：

- `nvda_remote` 的 remote 特性明顯，應只接入共用的 shell/mode/lifecycle，避免把 remote 特例污染平台層。
- `RuntimeState` 目前偏 remote-centric，不適合作為工具 app 平台的共用 state root。

## 針對既有 app 的落地方式

### key_echo

`key_echo` 應作為第一個完整接入平台的 app。

第一階段可先只有一個 mode：

- `echo_keys_mode`
  - enter hotkey: `Enter`
  - exit hotkey: `Escape`
  - active behavior: speak pressed key

之後若要新增：

- `echo_shortcuts_mode`
- `speak_selection_mode`
- `announce_key_category_mode`

只需新增 mode，無須重做 shell。

### nvda_remote

`nvda_remote` 應分兩段接入：

1. 先接入通知區圖示 shell、panel controller、speech settings controller
2. 再把 control mode 的 capture lifecycle 接到 `ModeManager`

它的 mode 可先保留單一：

- `remote_control_mode`
  - enter hotkey: `F11`
  - exit hotkey: `F11`
  - active behavior: remote key forwarding

但以下內容繼續留在 app-specific 層：

- `RemoteSession`
- `MessageRouter`
- connection status handling
- clipboard push/set 規則

## 重構順序

### 第一階段

抽出 `SpeechSettingsController`，合併兩份重複的 speech settings use case，並讓 `key_echo` 與 `nvda_remote` 同時接入。

目的：

- 低風險
- 高收益
- 先建立平台第一個穩定共用 capability
- 讓兩個 app 從第一步就共同驗證共用層是否合理

### 第二階段

引入 `PanelController`，讓主面板與語音設定面板都改為關閉只隱藏，並同步套用到 `key_echo` 與 `nvda_remote`。

此階段可先不接系統通知區圖示，先把視窗生命週期矯正。

### 第三階段

引入 `TrayAppShell` 與共用圖示選單，並讓 `key_echo` 與 `nvda_remote` 都先完成常駐系統通知區圖示、主面板開啟、語音設定開啟、由選單結束程式的基本流程。

完成後 app 啟動模型應改為：

- app 啟動後常駐系統通知區圖示
- 主面板透過圖示選單開啟
- 語音設定透過圖示選單開啟
- 程式結束只走圖示選單的「結束」

### 第四階段

引入 `ModeManager`，先讓 `key_echo` 以單一 mode 接入並驗證 contract。

此階段只讓 `key_echo` 完整接入 mode 平台，目的不是偏向 `key_echo`，而是先用較簡單的 app 驗證：

- `ActivationMode` 介面是否穩定
- enter/exit hotkey contract 是否足夠
- active keyboard routing 是否清楚
- mode 與 panel/圖示 shell 的邊界是否乾淨

### 第五階段

讓 `nvda_remote` 接入 `ModeManager` 的共用 active/inactive lifecycle，但保留 remote-specific orchestration。

此階段只接入以下共用能力：

- mode enter/exit lifecycle
- active/inactive capture switching
- active key routing contract

此階段仍保留以下 app-specific 邏輯：

- `RemoteSession`
- `MessageRouter`
- connection status handling
- clipboard push/set 規則

這樣可以驗證平台是否也適用於較複雜 app，同時避免一開始就把 remote 特例壓進平台核心。

### 第六階段

以第三個新工具 app 驗證平台是否真的降低新增成本。

驗收標準是：

- 新 app 不需重做通知區圖示 shell
- 新 app 不需重做 speech settings panel
- 新 app 不需重做 active/inactive capture 切換
- 新 app 只需註冊 mode、主面板與少量 app-specific use case

## 驗證策略

本設計採用「雙 app、分階段驗證」。

原因：

- 若只讓 `key_echo` 接平台，平台可能退化成只服務簡單 app 的抽象。
- 若一開始就讓 `key_echo` 與 `nvda_remote` 同時完整接入 `ModeManager`，則風險與除錯成本過高。

因此驗證方式分成兩層：

1. `key_echo` 與 `nvda_remote` 都要先共同驗證 shell/panel/speech settings 的共用層。
2. `ModeManager` 則先由 `key_echo` 驗證 contract，再由 `nvda_remote` 驗證平台邊界能否承受較複雜的 remote app。

這個順序的目的，是同時兼顧：

- 平台設計是否真的通用
- 問題定位是否夠容易
- `nvda_remote` 特例是否會污染平台核心

## 風險與取捨

### 風險 1：過早抽象成繼承架構

若一開始就做 `BaseAppFacade`，短期可減少重複碼，但長期很容易因 `nvda_remote` 特例而被大量 hooks 與條件分支污染。

取捨：

- 本設計偏好 composition over inheritance

### 風險 2：把 remote-specific state 帶進平台層

若讓平台共用 `RuntimeState` 或 `RemoteSession` 觀念，未來小工具 app 會被不必要的 remote 概念綁住。

取捨：

- 平台只處理 shell 與 mode lifecycle
- remote 相關狀態與流程留在 `nvda_remote`

### 風險 3：過度 generic 化 hotkey 模型

若一開始就要支援任意 command、可編輯 mappings、持久化設定，範圍會大幅膨脹。

取捨：

- 本階段只處理 mode enter/exit hotkey 與 active keyboard behavior

## 測試策略

### 單元測試

新增或調整以下測試類型：

- `SpeechSettingsController` 的 backend/voice/rate/pitch/volume 行為
- `ModeManager` 的 mode 註冊、單一 active mode 保證、切換失敗恢復
- `PanelController` 的 close-to-hide 行為
- `TrayAppShell` 的 menu action wiring

### 整合測試

保留並擴充：

- `key_echo` 進入 active、離開 active、按鍵處理流程
- `nvda_remote` control mode 進出與 capture lifecycle

### 行為驗證

至少驗證以下情境：

1. app 啟動後不自動開主面板，僅常駐系統通知區圖示
2. 點圖示選單的主面板可顯示視窗
3. 關閉主面板只隱藏，不退出 app
4. 點圖示選單的語音設定可顯示共用面板
5. 點圖示選單的結束才真正關閉 app
6. 同一 app 內多個 mode 不會同時 active
7. active mode 的 exit hotkey 可正常恢復 idle capture

## 實作建議摘要

本階段最重要的不是再引入新的 pattern，而是把以下四個邊界穩定下來：

1. app shell boundary
2. mode boundary
3. shared panel boundary
4. remote-specific boundary

只要這四個邊界站穩，未來新增小工具 app 的成本就會顯著下降；反之，如果先做 event bus、base facade、通用大狀態機，會得到更抽象但不更好用的架構。
