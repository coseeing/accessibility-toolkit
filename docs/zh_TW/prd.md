# accessibility-toolkit 產品需求文件

這份文件定義 `accessibility-toolkit` 的產品定位。它說明這個 toolkit 為什麼存在、是替誰服務、應提供哪些能力，以及應如何衡量成功。它不是主要的安裝指南，也不是架構導覽文件。

## 1. 執行摘要

`accessibility-toolkit` 是一套以 Python 開發的桌面無障礙應用工具套件，提供共享的鍵盤輸入擷取、mode-based 事件處理、語音／輸出服務，以及可重用的工具型應用殼層。這份產品文件的目標，是把目前的 repository 明確定義為一套支援多個無障礙 app 的 toolkit，而不是把共享執行期基礎設施視為單一 NVDA Remote client 的副產品。如果這個定位成立，toolkit 能降低重複工程成本、加快新無障礙桌面 app 的開發速度，並為內部 app 開發與未來重用建立穩定基礎。

## 2. 問題陳述

### 誰有這個問題？

- 使用 Python 開發桌面無障礙應用的開發者
- 在同一個 codebase 中演進多個桌面無障礙 app 的維護者
- 將無障礙工作流程從強耦合的 NVDA add-on 環境中遷出的開發者

### 問題是什麼？

桌面無障礙應用一再需要同一套基礎設施：

- 鍵盤與快速鍵擷取
- mode 進入與退出行為
- 語音後端選擇與輸出控制
- 可重複使用的桌面工具殼層
- 共享執行期與 app 專屬行為之間的清楚分界

如果沒有 toolkit，每個 app 都傾向自行實作這些 concern，或把它們和 domain logic 糾纏在一起。

### 為什麼痛？

- 新 app 一開始就要重做基礎 plumbing，而不是先交付使用者價值
- 共享行為在不同 app 之間容易分岔，後續維護更困難
- 平台專屬細節容易一路滲進 business logic
- 把獨立無障礙工具從 NVDA runtime 假設中遷出時，成本與風險都變高

### 證據

這裡的證據來自 repository 本身的演進歷程：

- 專案最早是 NVDA Remote client，之後才逐步抽出共享輸入、輸出、bootstrap 與 shell 層
- `key_echo` 的存在，就是為了驗證共享輸入／輸出基礎不是 remote 專屬
- `access8graph` 的存在，就是為了驗證同一套 foundation 也能支撐非 remote 的語音導覽工具
- 目前的專案文件已經把 repository 描述為一套承載多個 app 的 toolkit

## 3. 目標使用者與 Persona

### 主要 Persona：無障礙 App 開發者

- 角色：使用 Python 開發桌面無障礙工具的工程師
- 目標：不重做輸入、語音與殼層基礎設施，就能交付 app 專屬功能
- 痛點：
  - 低階輸入處理容易出錯
  - 語音後端 wiring 很重複
  - 跨平台桌面支援成本高

### 次要 Persona：Repository 維護者

- 角色：同時維護共享 toolkit 與多個具體 app 的維護者
- 目標：保持共享行為一致，同時讓不同 app 保有差異
- 痛點：
  - runtime wiring 重複
  - toolkit 與 app 邊界不夠清楚
  - 產品、架構與實作文件之間容易漂移

### 次要 Persona：NVDA Add-on 遷移作者

- 角色：把無障礙工作流程從 NVDA runtime 相依中遷出的開發者
- 目標：保留既有互動模式，同時改用獨立桌面執行期
- 痛點：
  - 舊程式預設 NVDA runtime API 一定存在
  - 取代執行期基礎設施的成本很高

### Jobs to be Done

- 當我建立桌面無障礙工具時，我希望有共享執行期能力，讓我能專注在使用者價值，而不是基礎設施。
- 當我維護多個無障礙 app 時，我希望共享行為只定義一次，讓 app 保持一致且可測試。
- 當我遷移依賴 NVDA 的工具時，我希望有可重用的桌面基礎，保留互動模式而不必依賴 NVDA runtime。

## 4. 策略脈絡

### 產品目標

- 將 repository 從單一專案型 client 重新定位為可重用的無障礙 toolkit
- 降低未來新桌面無障礙 app 的工程成本
- 為實驗性 app、遷移工作與參考 app 建立穩定共享底座
- 讓新加入的協作者與未來採用者更容易理解這個 repo

### 為什麼是現在？

repository 已經跨過了需要 toolkit framing 的門檻：

- 現在已經有多個使用者目的不同的 app
- 共享 bootstrap、輸入生命週期、speech 與 shell 層都已經存在
- 專案名稱與頂層文件正在往 toolkit 概念收斂

如果產品定位沒有跟上實作現況，這個 repository 會變成技術上可重用，但概念上仍然讓人困惑。

### 機會

這份 PRD 不估算外部市場規模。眼前的機會主要是產品與工程槓桿：

- 更快交付新的桌面無障礙 app
- 更低成本地遷移依賴 NVDA 的功能
- 若未來要公開或分享，能有更清楚的對外定位

### 替代方案

今天實際可選的替代方案是：

- 每個無障礙 app 都各自實作一套基礎設施
- 繼續依賴 NVDA runtime 假設
- 用一般 GUI 與 TTS 函式庫自行拼裝，但沒有共享 app 模型

`accessibility-toolkit` 的差異化在於：

- HID-first 鍵盤處理
- mode-based 生命週期管理
- 共用語音／輸出服務
- 可重複使用的工具型 app shell
- 已由多種不同 app 類型實際驗證可重用性

## 5. 解決方案概述

### 高階描述

`accessibility-toolkit` 會成為目前 repository 中共享 runtime 與 app 平台的產品識別。它會持續承載具體的參考 app，同時對協作者與未來 app 建構者提供一個一致的 toolkit 故事。

### 核心產品能力

1. 共享輸入基礎
- 將原生鍵盤與快速鍵輸入正規化成共享模型
- 提供一致的 idle / active 生命週期行為

2. Mode-based 事件處理
- 支援 mode 的進入、退出與 active keyboard routing
- 避免每個 app 自己重做 capture 切換與 mode state 管理

3. 共用語音／輸出服務
- 提供穩定的 speech facade，以及後端與設定控制
- 以中心化方式管理輸出順序

4. 可重用的桌面工具殼層
- 提供共用的 tray/menu shell 行為與設定入口
- 支援工具型 app 的視窗生命週期慣例

5. 建立在其上的 app 專屬 orchestration
- domain logic 保留在各 app 內
- 讓 remote control、key echo 與 graph navigation 共存在同一套共享 runtime 上

### 參考使用流程

#### Flow A：開發者用 toolkit 建立新 app

1. 開發者採用 toolkit 的 runtime 模型
2. 開發者把 app 專屬 service 接到共享輸入／輸出與 shell 層
3. 開發者定義 mode 的進入、active handling 與退出行為
4. app 使用共享 runtime 基礎設施啟動

#### Flow B：使用者執行 `nvda_remote`

1. 使用者啟動 app
2. 使用者連線到 NVDA Remote relay
3. 使用者進入 control mode
4. toolkit 管理 capture 生命週期與本地 speech 基礎設施
5. app 專屬邏輯處理遠端轉送與 relay 訊息

#### Flow C：使用者執行 `access8graph`

1. 使用者啟動工具 app
2. 使用者選取 `.graphml` 檔案
3. 使用者啟動 navigation mode
4. toolkit 管理輸入啟用與語音輸出
5. app 專屬圖形導覽邏輯驅動語音探索

## 6. 成功指標

### 主要指標

- repository 中有多少個 app 使用共享 toolkit runtime 模型，而不需要另起一套基礎設施分支

### 次要指標

- startup/runtime wiring 有多少比例留在共享 toolkit 層，而不是 app-local duplication
- 共享 toolkit 行為的測試覆蓋度
- 新增一個工具型 app 所需的時間與程式碼量
- README、架構規格與 PRD 之間的文件一致性

### 目標

現況：

- 3 個 app 以不同深度使用共享 foundation
- toolkit framing 已存在，但名稱與文件仍在收斂中

下一個里程碑：

- 3 個現有 app 都被清楚描述為 toolkit consumer
- 能在不發明新 runtime pattern 的前提下加入第 4 個 app
- 頂層文件、建置指引與產品定位都一致反映 toolkit 身分

## 7. 使用者故事與需求

### Epic Hypothesis

如果把目前共享 runtime 正式定義為 `accessibility-toolkit`，那麼開發者與維護者就能更快、更一致地建立與演進桌面無障礙 app，因為輸入、輸出、mode 與 shell 基礎設施已經以可重用的產品能力存在。

### User Story 1：共享輸入生命週期

作為無障礙 app 開發者，我希望有共享的 idle / active 鍵盤生命週期，這樣我就能實作 hotkey-driven mode，而不必自己寫一套 capture 切換邏輯。

#### 驗收條件

- toolkit 暴露共享 activation 模型，支援 hotkey-driven mode 進入與 active keyboard handling
- toolkit 在正常情況下避免 idle hotkey capture 與 active full-keyboard capture 重疊
- activation 失敗時可以乾淨地回報給 app

### User Story 2：共享語音與輸出

作為 app 開發者，我希望有共享的 speech/output service，這樣我就能提供語音回饋，而不必直接綁定 backend 專屬程式碼。

#### 驗收條件

- app 可以使用穩定的 speech facade 來做播放、取消、backend 選擇與 voice 設定
- 輸出順序控制由共享服務提供
- app 可以重用共享的語音設定 UI 行為

### User Story 3：共享工具型 Shell

作為要維護多個工具型無障礙 app 的人，我希望有共用的工具殼層，讓視窗生命週期與設定入口在不同 app 之間保持一致。

#### 驗收條件

- toolkit app 可以採用共享桌面 shell 模式
- 工具型 app 的主視窗在關閉時可以隱藏，而不是直接退出
- 主面板、語音設定與離開等共用選單動作可被重用

### User Story 4：App 專屬 Domain 隔離

作為 toolkit 維護者，我希望 domain logic 留在共享 toolkit 核心之外，這樣 toolkit 才能真正重用於不同 app 類型。

#### 驗收條件

- `nvda_remote`、`key_echo` 與 `access8graph` 都把 domain 行為保留在 app-local service 與 flow 中
- 共享 toolkit 程式碼不需要知道 remote protocol 語意或 graph navigation 規則
- 共享服務不需匯入 app 專屬 module 也能使用

### User Story 5：支援遷移

作為將無障礙工作流程從 NVDA 相依環境中遷出的開發者，我希望有一個可重用的獨立桌面基礎，這樣我就能在移除直接 NVDA runtime 相依的同時保留既有互動模式。

#### 驗收條件

- toolkit 文件能清楚說明共享輸入、輸出與 shell 的角色
- 參考 app 同時展示 remote-control 與 non-remote 的使用情境
- 遷移後的 app 邏輯不需假設 NVDA runtime API 一定存在

### 限制條件

- 需要 Python 3.11+
- 實機執行驗證目前以 Windows 與 macOS 為主
- NVDA Controller 語音整合仍然是 Windows 專屬
- `nvda_remote` 必須維持既有 NVDA Remote relay 相容性

### 邊界情況

- 某些按鍵可能同時需要 system pass-through 與 app-side handling
- 有些 app 比其他 app 更自然地符合 tool-shell 模型
- toolkit 身分不應抹平各 app 真正有意義的差異

## 8. 不在範圍內

- 以新網路協定取代 NVDA Remote relay protocol
- 建立 plugin marketplace 或動態 plugin system
- 立即支援所有桌面平台
- 為所有無障礙 app 提供完整視覺設計系統
- 將 toolkit 變成 hosted service 或 cloud platform
- 在這個階段承諾公開發佈套件
- 只為了抽象而重寫現有 app logic

## 9. 相依條件與風險

### 技術相依

- 穩定的 Windows 與 macOS adapter 行為
- 透過 `pyttsx3` 與 NVDA Controller 提供的共享語音後端支援
- wxPython 桌面 UI 支援
- 共享輸入模型與 app 專屬需求之間持續維持相容

### 外部相依

- Windows 上的 NVDA Controller DLL
- `nvda_remote` 所需的 NVDA Remote relay 相容性
- `access8graph` 所需的 GraphML 輸入資料

### 風險

#### 風險 1：toolkit 故事比實際邊界還清楚

如果命名與文件更新的速度快過程式邊界，產品可能看起來比實際更可重用。

Mitigation：

- 在文件與程式碼中清楚維持 toolkit/app 邊界
- 用現有參考 app 作為具體 proof point
- 避免聲稱尚未支援的泛化能力

#### 風險 2：平台假設重新滲回 app logic

如果抽象還不夠完整，app 程式碼可能重新引入 Windows 或 macOS 專屬假設。

Mitigation：

- 持續以 HID-first 規則作為預設共享模型
- 持續測試 adapter 邊界
- 優先使用共享生命週期政策，而不是 app-local 的重做邏輯

#### 風險 3：產品化只停留在文件層

如果 repo 改名了，但沒有真的被當成產品表面來經營，它仍然會很難採用。

Mitigation：

- 對齊命名、README、架構規格、PRD 與建置指引
- 以後續 app 新增作為 toolkit 模型是否成立的驗證

## 10. 開放問題

- 這個 repository 是否應繼續維持 monorepo 加參考 app 的形式，還是未來把 toolkit code 與 example apps 分開？
- 長期的發佈模式是什麼：內部 toolkit、開源 repo、Python package，還是三者並存？
- 現有共享 shell 行為中，哪些應成為穩定的公開 API surface？
- 下一個能驗證 toolkit 抽象是否足夠穩健的候選 app 是什麼？
