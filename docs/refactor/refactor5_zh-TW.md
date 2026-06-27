# 架構重構審查 v5

## 1. 審查範圍

本文件對照以下資料與目前 `src/` 程式碼，提出下一階段重構方向：

- `docs/refactor/refactor4.md`
- `docs/superpowers/specs/`
- `docs/superpowers/plans/`
- `docs/superpowers/specs/2026-06-26-access8graph-facade-and-shared-speech-settings-design.md`
- `docs/superpowers/plans/2026-06-26-access8graph-facade-and-shared-speech-settings-implementation.md`

審查方法同時採用：

- Design Patterns：確認現有模式是否真的降低耦合，以及下一階段適合採用哪些模式
- SOLID：檢查責任、擴充點、介面大小與依賴方向
- 漸進式交付：即使核心採完整改寫，仍以可獨立驗證的 milestone 控制風險

本文件只提出重構設計與建議，不包含實作。

## 2. `refactor4.md` 完成狀態

`refactor4.md` 建議的主要項目已大致完成：

1. Access8Graph flow lifecycle 已抽至：
   - `GraphSelectionUseCase`
   - `Access8GraphNavigationSession`
   - `MrtFlowFactory`
2. Access8Graph command dispatch 已抽至：
   - `Access8GraphKeyTranslator`
   - `Access8GraphCommandDispatcher`
3. Speech settings 已有獨立的：
   - `SpeechSettingsFacade`
   - `SpeechRuntimeSettingsCoordinator`
4. `application.output.Manager` 已移除。
5. `application.keyboard` 的內容正在移入 `application.input`，方向符合 package cohesion。

因此，下一階段不應再把「縮小 Access8Graph app service」或「移除 output
manager」列為主題。現在最高槓桿的問題已經往內移到 Access8Graph navigation
core，以及幾個仍不清楚的 package boundary。

## 3. 主要結論

建議下一階段採兩段式策略：

1. 先完成低風險的 package boundary 與 compatibility cleanup。
2. 再完整改寫 Access8Graph navigation flow，以可擴充的宣告式 transition
   table 取代目前的 State class hierarchy。

Access8Graph 不建議先做機械式拆檔。`src/apps/access8graph/flow.py` 的問題不只是
955 行，而是 20 個 state 皆可直接操作完整 `MrtFlow`、navigator dictionary、
message queue 與 view。若只把 class 搬到不同檔案，God Context、動態 dispatch
與隱性 transition 仍然存在。

核准的目標方案是：

> Declarative transition table + injected action handlers

新架構完整達到行為 parity 後，production path 應一次切換，不保留新舊 flow
並存或 compatibility adapter。

## 4. Design Patterns 審查

### 4.1 Access8Graph State Pattern

目前 `MrtFlow` 使用 State Pattern，但有以下問題：

- transition 分散在各 state method 的 `self.flow.state = ...`
- command 透過 `getattr(self.state, key)()` 動態派送
- state 可直接讀寫整個 flow 與 navigator
- view 建立、navigation mutation、message、speech policy 混在同一流程
- transition graph 無法在不執行程式的情況下完整檢查
- 新增 command 或 state 時，需要修改 translator、state class 與隱性 transition

判斷：

- 問題不是缺少 State Pattern，而是目前的物件式 State Pattern 缺乏窄 context
  與顯式 transition model。
- 下一步應改為 Table-Driven State Machine，而不是把現有 state classes 分檔。

建議模式：

- **Table-Driven State Machine**：集中描述 source、command、guard、action、target
- **Command**：以 typed `NavigationCommand` 取代 command dictionary
- **Strategy / Ports**：注入 guard 與 action handlers
- **Presenter**：將 speech、cancel、beep policy 與 transition execution 分離
- **Factory**：由 `MrtFlowFactory` 組裝 transition engine、context 與 handlers

### 4.2 Access8Graph Command Boundary

目前 translator 與 dispatcher 已經形成可用邊界，但 translator 回傳：

```python
{"key": "down", "repeat": 0, "pressing": 0}
```

其中 `repeat` 與 `pressing` 在目前 flow 並未形成穩定 domain contract，`key` 也仍
以任意字串驅動 `getattr`。

建議：

- translator 回傳 `NavigationCommand | None`
- command 使用 enum 或 frozen dataclass
- dispatcher 只依賴 `NavigationFlow` protocol
- flow 接收 typed command 並回傳 `TransitionResult`
- 不保留 dictionary compatibility path

### 4.3 Facade

三個 app service 目前合理地扮演 UI-facing Facade，但 facade 仍直接組裝部分 use
case 與具體 collaborator。這不是下一階段最優先問題，因為 bootstrap 已集中大部分
runtime wiring。

建議：

- 保留 app service 作為 facade，不再以「class 行數」為理由持續拆分
- 只有在 collaborator 可被獨立替換或已有明確 reuse 時才移出組裝責任
- app service consumer 應依賴窄 protocol，不應因 `Capabilities` 而取得不需要的能力

### 4.4 Adapter / Port

`SpeechEngineConfigStore` 位於 `application.config`，但它直接執行 JSON 與 filesystem
I/O；`SpeechRuntimeSettingsCoordinator` 又直接依賴此具體 class。

建議：

- application 層定義 `SpeechSettingsStore` protocol
- JSON 實作移到 adapter，例如 `adapters/config/json_speech_settings.py`
- coordinator 只依賴 protocol
- 保留現有 JSON schema 與容錯行為

這比單純把 `config.py` 搬到 `application/output/speech` 更符合 Dependency
Inversion。

### 4.5 UI Shell

下列檔案位於 `apps/shared`，但直接屬於 wx UI：

- `tool_app_shell.py`
- `tray_icon.py`
- `panel_controller.py`

建議移至 `ui/shared`。這是 ownership 修正，不需要新增抽象層。

## 5. SOLID 審查

| 原則 | 現況 | 主要問題 | 建議 |
|---|---|---|---|
| SRP | app service 已比 v4 更聚焦 | `MrtFlow` 與 state 同時處理 transition、navigation mutation、view、message、output | 拆成 engine、context、action handlers、presenter |
| OCP | 新增 state/command 需修改多處隱性邏輯 | `getattr` dispatch 與 state method 使 transition graph 不可檢查 | 以 declarative table 註冊規則與 handlers |
| LSP | 目前沒有明顯 subtype substitution defect | `State` subclasses 對 `view`、navigator shape 的隱性要求不同 | 移除該 hierarchy，改用規則與明確 handler contract |
| ISP | `SpeechServiceProtocol` 有 17 個 method | 只需 speak/cancel 的 consumer 也依賴 settings 與 lifecycle API | 依 output、settings、lifecycle 用途拆小 protocols |
| DIP | coordinator 依賴 JSON store；部分 app code 依賴 broad `Capabilities` | application policy 知道具體 persistence；consumer 能看到不需要的 output 能力 | 導入 store port，並在 use case constructor 使用窄 output protocol |

### 5.1 SRP 優先問題

最高優先：

- `apps/access8graph/flow.py`
- `apps/access8graph/graphml/mrt_navigator.py`
- `apps/access8graph/graphml/model.py`

其中只有 `flow.py` 建議納入下一階段核心改寫。GraphML model 與 navigator 雖然也大，
但同時重寫會讓 transition parity 難以判斷，應留待 flow 穩定後另案處理。

### 5.2 ISP 優先問題

`Capabilities.speech` 目前型別為完整 `SpeechServiceProtocol`。可逐步拆成：

- `SpeechOutputPort`：`speak`、`cancel`、`pause`
- `SpeechSettingsPort`：engine、voice、rate、pitch、volume
- `SpeechLifecyclePort`：`shutdown`

具體 `SpeechService` 或 `QueuedService` 可以同時實作多個 protocol，但 consumer 只
宣告實際需要的介面。這是 structural typing，不需要建立多層 wrapper。

### 5.3 Package Cohesion

建議調整：

- `application.state` 的 `RuntimeState`、`ConnectionState`、`ControlState` 只被
  NVDA Remote 使用，移至 `apps/nvda_remote/state.py`
- speech compatibility shims 應移除：
  - `apps/shared/speech_settings_controller.py`
  - `apps/key_echo/use_cases/speech_settings.py`
  - `apps/nvda_remote/use_cases/speech_settings.py`
- UI shell 類別移至 `ui/shared`
- `application.events` 目前仍有跨 app 的實際使用，可暫時保留；不應只為了目錄整齊
  而拆分

## 6. Access8Graph 目標架構

### 6.1 核心元件

#### `NavigationCommand`

- typed enum 或 frozen dataclass
- 表達 `UP`、`DOWN`、`LEFT`、`RIGHT`、`CONFIRM`、`HELP` 等 domain command
- keyboard translator 是 HID 到 command 的唯一轉換邊界

#### `NavigationStateId`

- 定義穩定 state identity
- 取代散落的 `"direction_run"` 等字串
- transition table、context 與測試共用同一組 ID

#### `TransitionRule`

每條規則至少包含：

- source state
- command
- optional guard ID
- action ID
- target state，或由 action result 明確決定的有限 target

規則只能描述協作關係，不直接包含 navigator 或 output I/O。

#### `TransitionEngine`

責任：

1. 依 current state 與 command 尋找規則
2. 執行 guard
3. 呼叫注入的 action handler
4. action 成功後才提交 target state
5. 回傳明確 `TransitionResult`

engine 不應：

- 建立 wx/UI object
- 直接 speak 或 beep
- 依賴 HID key code
- 透過 `getattr` 找 action

#### `NavigationContext`

只保存 state machine 所需的 session data，例如：

- current state
- background/return state
- selected navigation mode
- pending messages
- selection/session data

context 不應直接暴露完整 `MrtFlow` 給每個 action。

#### `ActionHandlers`

責任：

- 執行 navigator query 或 mutation
- 建立 view model
- 更新 context
- 回傳 action result 與 presentation data

handlers 透過 registry 注入 engine。table 使用穩定 action ID，不直接保存 bound
method，使 table 可驗證與測試。

#### `FlowPresenter`

責任：

- 將 transition/action result 轉成 speech items
- 決定何時 cancel speech
- 決定失敗時是否 beep
- 呼叫窄 `FlowOutput` port

### 6.2 資料流

```text
CapturedKeyEvent
    -> Access8GraphKeyTranslator
    -> NavigationCommand
    -> Access8GraphCommandDispatcher
    -> TransitionEngine
       -> guard registry
       -> action handler registry
       -> NavigationContext
    -> TransitionResult
    -> FlowPresenter
    -> speech / beep output
```

### 6.3 Transition Table 分組

完整切換後，table 可依 navigation mode family 分組：

- common/list/help transitions
- mode selection transitions
- direction exploration transitions
- undirected exploration transitions
- route planning transitions
- transfer/explore transitions

分組只為 ownership 與可讀性；載入後仍形成一個可完整驗證的 transition graph。

## 7. 錯誤處理

### 7.1 可預期拒絕

以下情況應形成 typed result，不使用 exception：

- current state 沒有對應 command
- guard 不成立
- action 判定目前無法移動或選擇

`TransitionResult` 應能區分：

- handled and transitioned
- handled without transition
- rejected
- unhandled

presenter 再依 result 決定 beep 與 speech。

### 7.2 Action 失敗

- engine 應在 action 成功後才提交 target state
- action 應盡可能先計算 result，再更新 context
- navigator 若有不可回復 mutation，handler 必須明確定義失敗語意並加測試

### 7.3 未預期例外

未預期例外不應由 table 或 engine 靜默忽略。例外應向上交由既有 app service
boundary：

- 發送 `ErrorRaised`
- 停止 navigation
- 保持目前錯誤 speech 行為

## 8. Transition Table 驗證

table 在測試與 runtime 組裝時應驗證：

- 相同 source + command 不得有無法判定順序的重複規則
- 所有 source 與 target state 必須存在
- 所有 guard ID 與 action ID 必須已註冊
- initial state 必須可達
- 非終止 state 應可由 initial state 到達
- help/menu state 必須有明確返回路徑
- navigation mode 必須有必要的 exit/escape 行為
- dynamic target 只能落在 action contract 宣告的 target set

驗證失敗應在啟動或 CI 立即失敗，不應等到使用者按鍵後才發現。

## 9. 建議 Milestones

### Milestone 1：低風險邊界與相容層清理

內容：

- 完成 `application.keyboard` 移入 `application.input`
- 移除 `SpeechSettingsController` compatibility shim
- 移除 Key Echo 與 NVDA Remote 的 speech settings alias modules
- 將 NVDA Remote runtime state 移至 app package
- 將 `ToolAppShell`、`ToolTrayIcon`、`PanelController` 移至 `ui/shared`
- 建立 `SpeechSettingsStore` port 與 JSON adapter
- 將 `SpeechServiceProtocol` 依 consumer needs 拆成窄 protocols

完成條件：

- import graph 符合 application 不依賴具體 JSON persistence
- `apps/shared` 不再包含 wx shell/tray code
- speech settings 只有一個正式 facade 名稱
- 所有既有單元與整合測試通過

### Milestone 2：舊 Flow 行為基準

內容：

- 補齊 `MrtFlow` characterization tests
- 建立 state/command transition matrix
- 記錄 speech items、beep、view 與 navigator side effects
- 特別覆蓋 help、return/background state、單一選項自動進入、transfer 與錯誤路徑

完成條件：

- 每個現有 state 至少有進入、主要 command、拒絕 command 與離開測試
- 現有隱性行為已被測試明文化
- 此 milestone 不更改 production flow 行為

### Milestone 3：建立新 Transition Engine

內容：

- 新增 typed command 與 state ID
- 新增 transition rule、engine、context 與 result
- 新增 guard/action registries
- 新增 presenter
- 建立完整 declarative transition table
- 使用 milestone 2 的案例驗證新 engine

完成條件：

- 新 engine 在測試中達到舊 flow 行為 parity
- table validation 全數通過
- production path 仍只使用舊 flow，避免半套混用

### Milestone 4：原子切換與舊架構移除

內容：

- `MrtFlowFactory` 改為建立新 flow
- command dispatcher 改用 typed command/result contract
- production path 切至 transition engine
- 刪除舊 `State`、`ListState`、`RunState` 與所有 subclasses
- 刪除 dynamic `getattr` dispatch 與 command dictionary
- 不新增 compatibility adapter

完成條件：

- key event 到 speech/beep 的整合測試通過
- UI、hotkey start/stop、error shutdown 行為不變
- repository 不再有舊 flow state hierarchy 的 runtime reference

### Milestone 5：模組收斂與完整性保護

內容：

- 依 mode family 拆分 transition tables 與 action modules
- 保持單一 graph validation
- 補上 unreachable/duplicate/unknown handler 等負向測試
- 更新架構文件與 module ownership 說明

完成條件：

- 每個 table/action module 有單一 navigation concern
- 新增 state 或 command 不需修改 engine
- 新規則可藉由註冊 table entry 與 handler 擴充
- 完整測試套件通過

## 10. 測試策略

### 10.1 Characterization Tests

重寫前先鎖定現況，不把目前行為是否理想與是否相容混為一談。若發現現有 bug，
應先記錄並另外決策，不在 parity 重寫中順便修正。

### 10.2 Engine Unit Tests

至少涵蓋：

- rule matching
- guard success/failure
- action success/rejection/exception
- state commit timing
- ambiguous rule rejection
- dynamic target validation

### 10.3 Handler Tests

每個 action handler 使用 fake navigator/context 測試：

- input contract
- navigator query/mutation
- context patch
- presentation result
- failure without invalid state commit

### 10.4 Table Contract Tests

以資料驅動方式驗證完整 transition matrix，不為每條規則重複撰寫大量 imperative
test setup。

### 10.5 Integration Tests

保留少量高價值路徑：

- 選擇 GraphML 並啟動 navigation
- direction exploration
- undirected exploration
- route planning
- help/menu return
- transfer
- invalid command beep
- exception -> error event -> stop navigation

## 11. 風險與控制

### 11.1 最大風險：隱性行為遺漏

現有 transition 分散在 state methods，部分行為由 property setter、`enter()`、
`exit()` 與 `refresh_view()` 間接觸發。

控制方式：

- milestone 2 先建立 transition matrix
- 新舊實作在測試中跑相同 scenario
- production 不做逐 state 混用

### 11.2 語音順序改變

`message`、hint 與 view display 的組合順序會影響使用者體驗。

控制方式：

- presenter 需有精確 sequence tests
- parity 測試比較 speech items 的順序，不只比較最後 state

### 11.3 Navigator Mutation

部分 action 直接變更 navigator current/source/destination/line/station。

控制方式：

- action handler 明確擁有 mutation
- transition engine 只在 action 成功後更新 state
- 高風險 transfer/route actions 加入 before/after snapshot assertions

### 11.4 過度抽象

table engine 可能被誤做成全 repository 通用 framework。

控制方式：

- engine 先留在 `apps/access8graph`
- 不為 Key Echo 或 NVDA Remote 強制導入
- 只有出現第二個相同需求後才評估上移 shared/application

## 12. 不建議在本階段進行

- 不先把 20 個舊 State classes 機械式拆成多個檔案
- 不保留 dict command compatibility layer
- 不讓新舊 state engine 長期並存
- 不同時重寫 GraphML parser、model 或 navigator
- 不重開 bootstrap/runtime provider 重構
- 不建立 repository-wide generic state-machine framework
- 不把 Scheduler concurrency 重構混入本階段
- 不變更 speech settings JSON schema

## 13. 後續候選項目

完成本階段後可重新評估：

1. `graphml/mrt_navigator.py` 的 query 與 mutable session state 是否應分離。
2. `graphml/model.py` 的 parsing、domain entity 與 graph query 是否應分層。
3. `application/output/scheduler.py` 的 concurrency contract 是否需要更明確的 state
   model 與 shutdown semantics。
4. `bootstrap/platform.py` 的 module-level factories 與 `PlatformProvider` 是否應收斂
   為單一 Abstract Factory API。
5. app service 是否仍需要完整 `Capabilities`，或可全面改用窄 output ports。

這些項目不應在 transition-table 改寫尚未穩定前同時啟動。

## 14. 下一階段完成定義

五個 milestone 全部完成時，必須符合：

- package ownership 清楚，wx UI 不位於 `apps/shared`
- speech settings compatibility shims 已移除
- application policy 不直接依賴 JSON config implementation
- NVDA Remote 專屬 state 不位於 shared application root
- speech consumers 使用符合需求的窄 protocols
- Access8Graph 使用 typed command
- Access8Graph transition graph 由 declarative table 表達並可完整驗證
- action handlers 經由注入提供 navigator 與 context mutation
- presentation/output policy 不在 transition table 或 engine 內
- 舊 State hierarchy、dynamic `getattr` dispatch 與 command dict 已移除
- navigation、speech、beep、hotkey 與錯誤行為維持相容
- 全部單元與整合測試通過

## 15. 最終建議

下一階段應先以 Milestone 1 修正低風險但明確的 ownership、ISP 與 DIP 問題，讓
package boundary 穩定；接著不要再延伸目前的物件式 State hierarchy，而是依
Milestone 2 至 5 建立完整行為基準、平行完成 declarative transition engine，最後
原子切換並移除舊架構。

這個方向比單純拆分 `flow.py` 更能提升可擴充性：新增 command、guard、action 或
transition 時，不需修改 engine，也不需讓新的 state class 取得整個 flow 的權限。
