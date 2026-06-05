# NVDA Remote Client 現況版 PRD

## 1. Executive Summary
NVDA Remote Client 是一個以 Python 實作的遠端控制端，第一階段先落地在 Windows，但核心目標不是只做 Windows client，而是把控制 NVDA 遠端機器的能力拆成可移植的架構，未來能延伸到 Linux、macOS、iOS 與 Android。現階段專案已完成核心協定、session、訊息路由、Windows 鍵盤擷取、剪貼簿同步、可切換的語音輸出後端與 wxPython GUI 外殼，且已在真實 Windows 環境完成人工驗證，因此目前可視為「已具備可用原型與移植基礎」的產品狀態。

## 2. Problem Statement

### 誰有這個問題
使用 Windows 桌面環境、且已在使用 NVDA Remote 的無障礙使用者或支援人員，需要一個獨立於 NVDA 主程式之外的控制端來連線到遠端 NVDA 工作站。

### 問題是什麼
現有需求不是單純的文字介面或模擬控制，而是要有真正的 Windows 鍵盤擷取、relay 連線、遠端 speech 與剪貼簿資料處理，以及一個可操作的 GUI。專案的目標是把這些責任拆分成可維護的模組，避免控制邏輯、平台整合與 UI 耦合在一起。

### 為什麼痛
- 使用者需要的是可直接操作遠端機器的控制端，而不是只讀狀態工具。
- 若功能綁死在 NVDA runtime 或單一輸出後端，後續移植、測試與除錯成本都會很高。
- 無障礙工具對輸入、輸出與連線穩定性要求高，任何協定或 Windows 整合缺口都會直接影響可用性。
- 目前若架構沒有先抽離平台差異，後續要擴展到 Linux、macOS、iOS 或 Android 時，會被 Windows 特有的 hook、clipboard 與 GUI 假設綁死。

### 現有證據
- README 已明確定義這是「Standalone NVDA Remote client for Windows」。
- 程式碼中已存在 relay transport、session state、message router、Windows keyboard hook、clipboard service 與 speech backend manager。
- 測試目錄已有單元與整合測試，表示核心 contracts 已被系統化驗證，但尚未完成真機端到端驗證。

## 3. Target Users & Personas

### Primary Persona: Windows NVDA Remote 使用者
- 角色：熟悉 NVDA 與 NVDA Remote 的終端使用者。
- 目標：從另一台 Windows 機器連入遠端 session，並能控制遠端機器。
- 痛點：需要穩定的連線、鍵盤轉送、語音回饋與剪貼簿同步。

### Secondary Persona: 技術支援人員
- 角色：協助使用者遠端排障或代操作的支援人員。
- 目標：快速建立連線、暫停/恢復控制、推送剪貼簿內容。
- 痛點：需要清楚的狀態回饋與可預期的失敗模式。

### Jobs To Be Done
- 建立到既有 NVDA Remote relay 的連線。
- 在連線後切換成控制模式，將 Windows 鍵盤事件轉發到遠端。
- 接收遠端 speech 與剪貼簿訊息，並在本機呈現。
- 在控制與本機操作之間切換，不讓使用者完全失去本機鍵盤控制權。

## 4. Strategic Context

### 產品目標
把 NVDA Remote 的控制端能力從 NVDA runtime 中抽離，形成一個可跨平台延伸的遠端控制架構。Windows 是第一個可用落地平台，但產品的主要動機是讓同一套核心 protocol、session 與 application 分層，能逐步移植到 Linux、macOS、iOS 與 Android。

### 為什麼現在做
- 現有需求已經足夠明確：要連線、控制、同步輸出，而不是重新定義 protocol。
- 如果不先在 Windows 上把核心邊界拆乾淨，後續移植到 Linux、macOS、iOS、Android 時，會反覆重做平台耦合邏輯。
- 專案已完成可行的分層架構，現在正是把它產品化、驗證化，並保留跨平台擴展能力的時間點。

### 架構方向
- `remote_core`：protocol、serializer、transport、session、routing、模型。
- `application`：狀態、服務編排、控制器。
- `adapters`：Windows 鍵盤、剪貼簿、NVDA controller DLL、pyttsx3 等後端。
- `ui`：wxPython GUI 外殼。

## 5. Solution Overview

### 目前已實作的能力
- 連線到 relay，送出 protocol version 與 join 訊息。
- 接收並處理 `channel_joined`、`version_mismatch`、`motd`、`client_joined`、`client_left`、`error`、`ping` 等訊息。
- 以 Windows keyboard hook 擷取本機鍵盤，將事件轉為 NVDA Remote `KEY` 訊息。
- 支援 clipboard push 與 remote clipboard 訊息處理。
- 支援 speech 輸出抽象，並可在 `NVDA Controller` 與 `pyttsx3` 之間切換。
- 提供 wxPython GUI，支援 connect/disconnect、start/stop control、clipboard push、speech backend 切換。
- 提供 F11 本機停止控制的熱鍵行為。

### 目前的產品邊界
- 產品定位為 Windows v1 控制端，但架構設計以未來跨平台移植為前提，不包含 follower mode。
- GUI 是薄殼，不承擔協定與 session 邏輯。
- core 模組不直接依賴 wx、Win32 hook 或 DLL 實作。

### 現況判定
這不是概念驗證而已，已經有可執行程式、測試與模組分層，並且已完成真實 Windows 機器上的手動端到端驗證；但它的價值不只在 Windows 本身，而是在於這套結構已經開始證明可以作為跨平台移植的基礎。現階段仍不能直接宣稱是完整上市版本，因為後續還需要持續擴充驗證範圍並把平台適配層往其他作業系統延伸。

## 6. Success Metrics

### 主要指標
- 真實 Windows 環境下可成功連線到既有 NVDA Remote relay 並完成 join。
- 鍵盤控制可穩定轉送到遠端機器。
- 遠端 speech 與 clipboard 訊息可在本機正確呈現。

### 次要指標
- 自動化測試可持續維持通過。
- GUI 可穩定切換連線、控制與語音後端。
- 本機停控熱鍵可正確釋放控制狀態。

### 驗收門檻
- 不依賴 NVDA Python runtime 也能啟動應用程式。
- 可在 Windows 上完成至少一次完整連線、控制、停止控制、斷線流程。
- 任何後端不可用時，系統需有可預期的 fallback 行為，而不是直接崩潰。

## 7. User Stories & Requirements

### Epic Hypothesis
如果我們提供一個獨立的 Windows NVDA Remote 控制端，使用者就能在不依賴 NVDA runtime 的情況下完成遠端控制、語音回饋與 clipboard 同步。

### 核心需求
- 使用者可以輸入 host、port 與 key 並連線。
- 系統在連線後自動完成 protocol version 與 channel join。
- 使用者可以啟動或停止控制模式。
- 控制模式啟動後，Windows 鍵盤事件會被轉發到遠端。
- 系統可接收 speech、pause、cancel、clipboard 訊息。
- 使用者可手動推送本機 clipboard 到遠端。
- 使用者可切換 speech backend。

### 行為要求
- 未連線時，控制按鈕不可啟用。
- 連線中時，host/port/key 欄位不可編輯。
- 停止控制後，連線可維持，但輸入轉送必須暫停。
- 發生連線錯誤時，GUI 需以可理解方式顯示錯誤。
- 若 SSL 驗證失敗，GUI 允許以 insecure 模式重試。

### 已知限制
- 目前僅針對 Windows。
- Braille、tone、wave 仍屬保留接口或簡化實作。
- secure desktop / SAS / follower mode 仍未納入 v1。

## 8. Out of Scope
- follower mode。
- 完整 braille 支援。
- 產線等級 tone / wave playback。
- secure desktop 與 full SAS handling。
- URL handler integration。
- 非 Windows 平台 adapter。
- 在 client 內啟動 local relay server。

## 9. Dependencies & Risks

### 依賴
- Windows 作業系統與其 keyboard hook、clipboard API。
- `wxPython` GUI runtime。
- NVDA controller client DLL 或系統上可用的對應檔案。
- 可用的 NVDA Remote relay/server endpoint。

### 風險
- 雖已完成一次或多次真機人工驗證，但仍可能存在未覆蓋到的協定相容性或 hook 行為差異。
- speech backend 切換涉及本機可用性，失敗時需確保 fallback 行為一致。
- `wxPython`、Windows hook 與 DLL 載入路徑都屬高風險整合點。
- 若 relay 端協定或版本行為與預期不同，session join 可能失敗。

### 緩解方式
- 以單元與整合測試維持 core contract。
- 在 Windows 真機上做最小可行的端到端 smoke test。
- 讓 `remote_core` 持續保持純邏輯層，避免平台耦合擴散。

## 10. Open Questions
- 目標 relay/server 的實際版本相容範圍是多少？
- 預設 speech backend 應該以 `NVDA Controller` 還是 `pyttsx3` 為主？
- 是否需要把連線參數與 backend 選擇納入正式設定檔的使用說明？
- 真機驗證時，最小可接受的 smoke test 清單要定義到什麼程度？
