# App Service 拆分設計

## 目的

透過將 app 層責任拆分為聚焦的 use case 物件，降低 `NvdaRemoteAppService` 與 `KeyEchoAppService` 的複雜度，同時保留目前行為，並維持 wx UI 整合的穩定性。

這是 bootstrap 抽取之後的下一個重構階段。目標不是重新設計整體架構，而是在不超出必要範圍變更既有 UI 契約的前提下，讓 app 層責任更小、更清楚，也更容易測試。

## 範圍

| 包含 | 不包含 |
|------|--------|
| 將 app 層責任拆分為聚焦的 use case | 重新設計 output 架構 |
| 為 `nvda_remote` 與 `key_echo` 引入薄型 app facade | 以 typed events 取代 dict/status flow |
| 在實務可行的前提下保留現有 UI-facing controller surface | 以更窄的 presenter 介面取代 wx UI 依賴 |
| 以同一套 mapping 機制統一狀態切換類 hotkey 處理 | 引入超出狀態切換範圍的一般 command-hotkey dispatch |
| 為新的 use case class 增加直接的單元測試 | 引入共用 base controller 或繼承階層 |
| 讓兩個 app 對齊到相同的 app-layer pattern | 重構 transport/session/protocol 架構 |

## 設計目標

1. 降低目前 app service class 內的 business logic 份量。
2. 將相同的 app-layer pattern 同時套用到 `nvda_remote` 與 `key_echo`。
3. 保留目前的 runtime 行為與 UI 行為。
4. 保持 dependency flow 簡單且明確。
5. 透過將規則移到較小的物件中，提升 unit-testability。
6. 統一兩個 app 的狀態切換類 hotkey 處理方式。

## 目前的問題

`src/apps/nvda_remote/service.py` 目前混合了多種責任：

- connection orchestration
- control mode lifecycle
- input forwarding rules
- transport event handling
- clipboard 相關行為
- speech backend settings 行為
- UI 導向的狀態分派

`src/apps/key_echo/service.py` 雖然小很多，但它仍然把 app orchestration 與 input/output 行為合併在同一個 app-specific service class 中。

兩個 app 目前對於會改變狀態的 hotkey 也採用不一致的處理方式：

- `nvda_remote` 使用 `F11` 進入／離開 control mode
- `key_echo` 使用 `Escape` 離開 echo mode
- `key_echo` 目前尚未提供對稱的 start hotkey 來進入 echo mode

這些本質上是同一類問題：hotkey 映射到狀態切換 action。這段邏輯不應繼續以一次性、app-specific 的硬編碼分支散落在事件處理中。

結果是 app 層呈現不均衡的形狀：

- 一個過大的 service，擁有太多變更理由
- 一個過小的 service，無法驗證可重用的 pattern

下一階段應讓兩個 app 遵循相同的結構 pattern，同時避免過早強迫導入共用 base class。

## 建議做法

使用 **facade 加上聚焦 use cases** 的 pattern。

每個 app 都擁有：

- 一個薄型 app facade，作為 UI-facing controller surface
- 數個承載 business logic 的聚焦 use-case 物件
- 一套以 mapping 為基礎的狀態切換 hotkey 機制

共享結構透過 pattern 對齊達成，而不是透過繼承。

### 為何採用這個做法

- 比起立即更動 UI 依賴更安全
- 比只做最小抽取、把大部分複雜度留在原處更有意義
- 避免過早抽象成共用 base controller
- 為後續 output/event/UI 重構建立乾淨的基礎
- 讓 `nvda_remote` 與 `key_echo` 的狀態切換行為收斂到同一個模型

## 目標結構

### `nvda_remote`

建議的 app-layer 拆分：

- `NvdaRemoteAppFacade`
- `ConnectionUseCase`
- `ControlModeUseCase`
- `InputForwardingUseCase`
- `SpeechSettingsUseCase`
- `StateTransitionHotkeyUseCase`

可能的檔案組織：

```text
src/apps/nvda_remote/
  facade.py
  service.py          # 若有需要，作為相容性 re-export 或過渡期 wrapper
  use_cases/
    __init__.py
    connection.py
    control_mode.py
    input_forwarding.py
    speech_settings.py
    state_transition_hotkeys.py
```

### `key_echo`

建議的 app-layer 拆分：

- `KeyEchoAppFacade`
- `EchoControlUseCase`
- `EchoInputUseCase`
- `SpeechSettingsUseCase`
- `StateTransitionHotkeyUseCase`

可能的檔案組織：

```text
src/apps/key_echo/
  facade.py
  service.py          # 若有需要，作為相容性 re-export 或過渡期 wrapper
  use_cases/
    __init__.py
    echo_control.py
    echo_input.py
    speech_settings.py
    state_transition_hotkeys.py
```

## 狀態切換類 Hotkey 模型

本階段應以同一套模型統一那些會進入或離開長生命週期 app mode 的 hotkeys。

本階段範例：

- `nvda_remote`
  - 未 controlling 狀態下按 `F11` -> 進入 control mode
  - controlling 狀態下按 `F11` -> 離開 control mode
- `key_echo`
  - 未 echo 狀態下按 `Enter` -> 進入 echo mode
  - echo 狀態下按 `Escape` -> 離開 echo mode

這些應被建模為：

```text
key event -> hotkey mapping -> state-transition action -> use-case function
```

### 本階段納入的內容

- 以 mapping 為基礎的狀態切換類 hotkey dispatch
- 每個 app 在程式碼中的預設 hotkey mappings
- 明確拆分 hotkey 比對與 business action 執行
- 在設計上預留未來從 config 載入 mappings 的能力

### 本階段不納入的內容

- 編輯 hotkey 的 UI
- 完整的自訂 hotkey config persistence
- 一般一次性命令的 generic command-hotkey dispatch
- 跨 app 的全域 hotkey registry

### 為何要限制範圍

狀態切換類 hotkeys 已足以統一目前的 `F11` / `Enter` / `Escape` 行為，而不需要把本階段擴張成完整的 command system。若現在一起處理一般 command hotkeys，將需要更廣泛的 dispatcher model、更多 action 類型與更大的 state/validation 範圍，會使本階段明顯變大。

## 責任拆分

### `NvdaRemoteAppFacade`

責任：

- 對外暴露 UI-facing controller surface
- 在單一 UI 動作跨越多個責任時協調 use cases
- 保留與既有 UI wiring 的相容性

非責任：

- 直接擁有 business rule
- 低階 transport 邏輯
- key forwarding 邏輯細節
- speech settings 規則實作

### `ConnectionUseCase`

責任：

- connect
- disconnect
- 更新 connection 相關狀態
- 協調 connection 動作所需的 transport lifecycle

非責任：

- key forwarding 規則
- control-mode toggle 規則
- speech backend 設定

### `ControlModeUseCase`

責任：

- start control
- stop control
- 強制進入／離開 control mode 時的狀態前置條件
- 協調屬於 control mode 的 hotkey 啟用／停用規則

非責任：

- transport connect/disconnect
- raw key-event forwarding 決策

### `InputForwardingUseCase`

責任：

- 處理 input events
- 決定 pass-through 或 suppress
- 套用 local stop-hotkey 的 business rules
- 透過適當的 collaborator 轉送 remote key messages

非責任：

- connection 建立
- speech backend settings
- UI 狀態格式化

### `SpeechSettingsUseCase`

責任：

- 切換 backend
- 對外暴露 selected backend
- 設定與查詢 voice/rate/pitch/volume
- 將 backend-setting 規則集中在單一位置處理

非責任：

- speech playback 實作
- queue/scheduler lifecycle

### `StateTransitionHotkeyUseCase`

責任：

- 評估已配置的狀態切換類 hotkey mappings
- 將符合的 key events 轉換為 app-level state-transition actions
- 將這些 actions 委派給正確的 app use case

非責任：

- 實作實際的 business state transition
- 狀態切換之外的一般 command dispatch
- UI-facing 狀態格式化

### `KeyEchoAppFacade`

責任：

- 對外暴露目前的 UI-facing controller surface
- 協調 echo control 與 speech settings use cases
- 協調狀態切換類 hotkey 處理

### `EchoControlUseCase`

責任：

- start echo
- stop echo
- 協調 echo mode 所需的 input-service lifecycle 動作

### `EchoInputUseCase`

責任：

- 將 input events 轉為 output actions
- 套用不屬於 hotkey mapping 的 echo 專屬輸入規則

### `key_echo` 中的 `SpeechSettingsUseCase`

`key_echo` 應使用與 `nvda_remote` 相同的 pattern shape，即使行為較簡單亦然。兩個 app 現階段不需要立即共用同一份實作，但它們應暴露相同的概念邊界。

## Hotkey Mapping 結構

本階段應以顯式 mappings 表示狀態切換類 hotkeys，而不是在程式中以每顆按鍵的硬編碼分支來實作。

概念上的形狀例如：

```python
{
    "toggle_control": ...,
    "start_echo": ...,
    "stop_echo": ...,
}
```

實際儲存型別可以調整，但架構上必須保留以下拆分：

1. 一層 hotkey matching，負責判斷 input event 是否映射到某個 action
2. 一層 action execution，負責呼叫對應 use case

### 本階段的預設 mappings

必備預設值：

- `nvda_remote`
  - `F11` -> `toggle_control`
- `key_echo`
  - `Enter` -> `start_echo`
  - `Escape` -> `stop_echo`

### Config 擴充性

本階段的設計應允許這些預設值在未來從 config 載入，但這個載入行為本身不必在此階段實作。

必要的設計限制：

- use cases 與 facades 不應以硬編碼 key constants 作為主要控制契約
- mapping 應保持可被未來的 config-backed source 取代

## 依賴方向

必須遵守的 dependency flow：

```text
UI -> app facade -> use cases -> existing lower-level services/protocols
```

規則：

1. UI 與 facade 溝通，而不是直接呼叫個別 use case。
2. facade 負責組合 use cases，但不應吸收它們的邏輯。
3. 每個 use case 只依賴它真正需要的 collaborators。
4. use cases 不應隨意彼此依賴；若需要跨 use-case 協調，應由 facade 負責，除非某個依賴方向明確且穩定為單向。
5. 不應在 facades 或 use cases 中加入新的平台分支。
6. hotkey matching 不應以零散的 key-constant 分支嵌入在不相干的 use case 中。

## 協作模型

此設計刻意避免引入共用 base class，例如 `BaseAppService` 或 `BaseAppFacade`。

原因：

- `nvda_remote` 與 `key_echo` 在結構上相似，但 business rules 仍有明顯差異。
- 若此時導入共用 parent，很可能只會捕捉到偶然的相似處，並把 remote-specific 行為塞進共用程式碼中。

本階段真正共享的資產是 pattern：

- 薄型 facade
- 聚焦 use cases
- 明確的 dependency direction
- 每個 use case 都有直接的單元測試

## 向後相容策略

本階段應保留目前的 UI-facing 行為。

建議策略：

- 保持傳入 wx UI 程式碼中的物件，在功能上仍與目前 controller surface 相容
- 先在該 surface 背後遷移實作
- 將 UI 介面收斂延後到後續階段

若有需要，`service.py` 可暫時保留為：

- facade 實作本身，或
- 包裹 `facade.py` 的相容性 wrapper/re-export

重要限制是維持行為連續性，而不是追求檔名純度。

## 錯誤處理

錯誤處理應被釐清，而不是被擴大。

規則：

1. use cases 應擁有 business-level failure decision。
2. facades 應將失敗轉換或傳遞為與目前 UI 可觀察行為一致的形式。
3. infrastructure 例外不應在 facade 中以零散方式到處捕捉；應盡可能在適當的 use-case 邊界處理。
4. 本階段不應引入新的全域 error/event framework。

範例：

- disconnected 狀態下嘗試 start control，仍屬於 control-mode 規則
- 不在正確狀態下嘗試送出 forwarded input，仍屬於 input-forwarding 規則
- 切換到無效 backend，仍屬於 speech-settings 規則
- 命中的 hotkey action 會委派給對應的狀態切換 use case，而該 use case 仍負責 guard conditions 與失敗行為

## 測試策略

本階段必須強化 app-layer 邊界的測試。

### 保留既有回歸覆蓋

驗證目前 app 行為的既有測試應保留並持續通過。

範例：

- `tests/unit/test_nvda_remote_app_service.py`
- `tests/unit/test_key_echo_app_service.py`
- 相關 wx composition tests

### 增加直接的 use-case 測試

每個新的 use-case class 都應擁有聚焦在自身規則的單元測試。

範例：

- connection 狀態轉換
- start/stop control 前置條件
- key forwarding suppress 規則
- hotkey mapping 到 state-transition action 的行為
- start/stop echo hotkey 行為
- speech backend 選擇與設定行為

### 增加 facade composition 測試

增加測試以驗證：

- facade 能正確將 use cases 接起來
- facade methods 委派給正確的 use case
- facade 不會重新實作已由 use-case 測試覆蓋的 business logic

## 遷移限制

本階段不得擴張成相鄰的重構主題。

具體來說，下列內容不應在本設計中一起處理：

- 重新設計 tone/wave/braille 的 output channels
- 以 typed events 取代 dict-based status payloads
- 重新設計 UI 依賴更窄介面的方式
- 重寫 transport/session/message-router 的責任切分
- 引入共用的 base app service/facade 繼承階層
- 增加超出狀態切換範圍的一般 command-hotkey framework
- 增加 hotkey 自訂的 UI/config 編輯能力

## 成功條件

當以下條件全部成立時，本階段即算完成：

1. `NvdaRemoteAppService` 被取代，或被縮減為薄型 facade 角色。
2. `KeyEchoAppService` 遵循相同的 facade/use-case 結構 pattern。
3. 核心 app business rules 被移入聚焦的 use-case classes。
4. 既有 UI-facing 行為維持相容。
5. 既有回歸測試持續通過。
6. 對抽取出的責任新增 use-case 單元測試。
7. 兩個 app 的狀態切換類 hotkeys 使用相同的 mapping-based 機制。
8. 沒有把新的架構階段一併拉進這次變更。

## 後續路徑

本階段的目的，是為後續工作鋪路，但不在本階段一併處理。

當此設計完成實作後，後續較合理的重構選項會更清楚：

- 收斂 UI-facing interfaces
- 引入 typed domain events/state models
- 重新設計多模態 output architecture

後續階段應建立在較小的 app-layer 邊界之上，而不是同時嘗試重塑 app layer 與 output/event architecture。
