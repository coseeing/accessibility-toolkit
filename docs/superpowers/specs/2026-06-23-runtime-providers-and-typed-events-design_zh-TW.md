# Runtime Providers And Typed Events 設計

## 目標

重整 runtime 組裝方式，以及 app / UI 事件邊界，讓這個 codebase 在不重複
bootstrap 邏輯、也不再依賴臨時拼湊的 status dictionary 的前提下，能支援更多 app、
平台與 UI flow。

這份設計涵蓋兩個依序進行的里程碑：

1. `M1`：runtime provider 抽取
2. `M2`：三個 app 全面的 typed event 遷移

這兩個里程碑預期分開 review 與 merge，但 `M2` 會明確建立在 `M1` 引入的結構之上。

## 現況

在 output package 重整之後，這個 codebase 的狀態比以前好不少：

- output 相關關注點現在集中在 `application.output`
- speech backend selection 已經隔離到 `application.output.speech`
- app runtime 的命名比以前一致
- 部分 app 專屬行為已經放在 `apps/*/use_cases/` 底下

目前主要的架構壓力集中在兩個地方：

1. runtime 組裝仍然在 `apps/*/main.py` 之間重複
2. app / UI status flow 仍然依賴結構鬆散的 dictionary

`bootstrap/platform.py` 目前也還是承擔過多責任。它現在同時混合了：

- 平台偵測
- lazy import 解析
- null fallback implementation
- clipboard 與 tone factory 行為
- speech backend selection

在 app 端，`NvdaRemoteAppService`、`KeyEchoAppService` 和
`Access8GraphAppService` 仍同時對外暴露面向 UI 的 controller 方法，並且負責較低層的
orchestration。這讓 event 與 status flow 很難安全演進。

## 非目標

這份設計不包含以下工作：

- 將 `NvdaRemoteAppService` 再拆成多個聚焦的 use-case class
- 將 output 重設計成完整的 channel-based `OutputBus`
- 用 typed wire model 取代 remote protocol payload
- 重寫 UI class 或 wx 結構，超出 typed event consumption 所需的最小範圍
- 導入完整的 dependency injection container 或 registry framework

這些仍然是合理的後續重構方向，但不屬於 `M1` 或 `M2` 的範圍。

## Milestone 1: Runtime Provider Extraction

### 意圖

移除 app entrypoint 中重複的 runtime 組裝，並建立共用的 bootstrap 邊界，用來處理平台與
output capability 的接線。

### 設計原則

- 保持 app `main.py` 輕薄
- 將共用 wiring 移到 `bootstrap/`
- 使用輕量的 provider object 搭配 builder function
- 不引入通用型 container
- 除非有充分理由要正規化，否則保留現有行為與 runtime 形狀

### 目標結構

`bootstrap/` 內預期的方向如下：

- `bootstrap/platform.py`
  - 平台 capability provider 的建構
  - 面向 provider 的 fallback 邏輯
- `bootstrap/output.py`
  - scheduler、speech、speaker、tone 與 capability 組裝
- `bootstrap/app_runtime.py`
  - app entrypoint 共用的 runtime wiring helper

如果周邊程式碼顯示有更合適的在地命名模式，檔名可以略作調整，但責任邊界仍應維持這樣的分工。

### 核心型別

`M1` 應引入少量而明確、位於 bootstrap 端的型別。

建議型別：

- `PlatformProvider`
  - 回答哪些平台支援的服務可用
  - 負責建立 input capture、hotkey capture、clipboard 與 tone output
- `OutputServices`
  - 封裝 runtime output 組件：
    - `scheduler`
    - `speech`
    - `speaker`
    - `capabilities`
- `AppRuntimeParts`
  - 可選的 helper bundle，提供共通 runtime wiring，讓各 app 再包進自己的 runtime dataclass

這些型別應維持小而具體。它們的目的不是演變成通用 framework abstraction。

### Runtime Builder 形狀

組裝流程應大致長這樣：

1. app `main.py` 向 bootstrap 取得平台支援的服務
2. app `main.py` 向 bootstrap 要求組裝 output services
3. app `main.py` 提供 app 專屬相依物件
4. app `main.py` 建立 app service 與 UI shell

也就是說，app `main.py` 仍然決定：

- 要實例化哪個 app service class
- 要實例化哪個 UI app class
- 要使用哪一組預設 hotkey 用法
- 有哪些 app 專屬相依物件，例如 transport 或 config store

但 app `main.py` 不應再直接組裝所有共用 runtime 組件。

### App Entrypoint 的預期結果

在 `M1` 之後，`apps/*/main.py` 應大致只剩下：

- 取得平台支援的服務
- 取得 output services
- 建立 app 專屬 service
- 建立 keyboard input service
- 建立 UI app
- 回傳 runtime dataclass

平台與 output 的細部組裝，不應再分散在三個 app entrypoint 裡。

### M1 的驗證條件

當以下條件都成立時，`M1` 才算完成：

- 三個 app entrypoint 明顯變薄
- 共用 runtime wiring 集中在 `bootstrap/`
- 平台 capability selection 不再在各 app main module 裡各自手寫
- 現有以 runtime 為主的測試仍能驗證 app 啟動組裝
- 完成這個里程碑不需要同步拆分 app service 責任

## Milestone 2: Typed Event Boundary

### 意圖

在三個 app 中，用 typed event 取代以 dictionary 為基礎、面向 UI 的 status 輸出。

### 範圍決策

`M2` 會一次套用到三個 app：

- `nvda_remote`
- `key_echo`
- `access8graph`

這不是單一 app 的試點。這個里程碑的重點，是在整個 repo 裡建立一套一致的 application / UI
event 邊界。

### 共用 Event 位置

共用 event 必須定義在：

- `src/application/events.py`

這個檔案是 application-level 共用 event model 的正式位置，供多個 app 與共用 UI /
controller code 使用。

### App 專屬 Event 位置

不屬於共用語意的 app-domain event，應放在各 app package 內。

例如：

- `src/apps/nvda_remote/events.py`
- `src/apps/key_echo/events.py`
- `src/apps/access8graph/events.py`

這樣可以避免 `application/events.py` 變成 remote 專屬或 graph 專屬語意的雜物堆放區。

### Event 分層規則

`application/events.py` 裡的共用 event，應描述跨 app 都有意義的 runtime 或 capability 狀態。

例如：

- `ErrorRaised`
- `SpeechBackendChanged`
- `InputCaptureChanged`
- `HotkeyCaptureChanged`
- `ClipboardAvailabilityChanged`

app 專屬 event 則應描述 app-domain 語意。

例如：

- NVDA Remote：
  - `RemoteConnectionChanged`
  - `RemoteControlChanged`
  - `RemoteTransportDisconnected`
- Access8Graph：
  - 若有需要，可加入 graph selection 或 navigation lifecycle event
- Key Echo：
  - 若有需要，可加入 mode 專屬 state event

### 邊界定義

typed event 遷移應先聚焦在以下邊界之間：

- app service
- 面向 UI 的 controller 或 listener

也就是說：

- app service 應在內部發出 typed event
- UI controller 應消費 typed event
- 以 dict 為基礎的 status payload 不應再是主要契約

如果遷移期間暫時需要相容層，可以使用一個薄薄的 adapter，將 typed event 轉成舊的 dict 形狀。
這個 adapter 是過渡用，不是新的長期公開 API。

### 與既有 `StatusEvent` 的關係

`application/events.py` 目前有 `StatusEvent`，本質上只是把通用 dict 形狀包成 typed wrapper。

`M2` 應該逐步離開這個模型。

目標不是：

- 一個泛用的 `StatusEvent` 再加上自由格式 payload

目標是：

- 多個明確的 event dataclass，具有穩定欄位與名稱

舊 wrapper 在遷移支援期間可以短暫保留，但不應成為這個里程碑的最終狀態。

### M2 的遷移策略

預期順序如下：

1. 在 `application/events.py` 定義共用 event dataclass
2. 視需要在各 app package 之下定義 app-domain event
3. 更新 app service，讓它們發出 typed event
4. 更新共用 UI / controller code，使其能接收 typed event
5. 更新 app 專屬 UI consumer，使其能接收 typed event
6. 在三個 app 全部完成遷移後，移除以 dict 為優先的 status flow

### M2 的驗證條件

當以下條件都成立時，`M2` 才算完成：

- 三個 app service 都以 typed event 作為面向 UI status contract 的主要形式
- 共用 event 定義集中在 `application/events.py`
- 有需要時，app-domain event 放在各 app package 之下
- UI / controller code 不再以原始 dict key 慣例作為主要契約
- 若存在相容 adapter，它必須清楚是過渡性且保持輕量

## 為什麼順序很重要

里程碑順序應維持為：

1. `M1`：runtime provider 抽取
2. `M2`：typed event 邊界

原因：

- `M1` 能先減少重複 wiring，並穩定 runtime assembly 的邊界
- 接著 `M2` 才能在更乾淨的 app / service / UI 邊界上進行
- 如果順序反過來，event 工作就會散落在仍然結構雜亂的 entrypoint 中

`M2` 不必和 `M1` 完全獨立，但在 `M1` 落地後，不應還需要額外的大規模 bootstrap churn。

## 測試策略

### M1

重點放在 runtime 組裝與啟動組成測試：

- app runtime build test
- bootstrap platform test
- 驗證共用組件是否正確接線的 app main test

行為應維持不變。大多數測試應該是調整適配，而不是全部重寫。

### M2

重點放在 event contract 與 UI 邊界測試：

- app service 的 event emission test
- 消費 typed event 的 controller 或 listener test
- 如果遷移期間存在 adapter，則加入 compatibility adapter test

目標是驗證穩定的 event contract，而不只是間接驗證 UI state effect。

## 風險

### M1 風險

- 太早過度抽象，做成 framework，而不是 helper layer
- runtime wiring 形狀改太多，迫使 app 發生不必要的 churn
- 將 provider 抽取和 app-service 拆分混在同一個里程碑處理

### M2 風險

- 發明一個巨大的 event union，結果變成另一層脆弱抽象
- 把共用 event 與 app 專屬 event 混在同一個 module
- 讓 repo 長期停留在 dict status 與 typed event 同時都是主要 API 的混合狀態

## 建議的下一步

這份設計之後，下一個具體步驟應該是只為 `M1` 撰寫 implementation plan。

這樣可以把第一階段的執行範圍收緊，先建立 `M2` 需要的 bootstrap 邊界，避免把兩個里程碑一次做成
過大的 implementation batch。
