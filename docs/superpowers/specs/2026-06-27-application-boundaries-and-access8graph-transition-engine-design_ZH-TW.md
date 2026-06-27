# 應用層邊界與 Access8Graph 轉移引擎設計

## 目標

本設計定義 `docs/refactor/refactor5.md` 之後的下一階段重構，依序完成兩個目標：

1. 修正剩餘的低風險應用層、轉接器與 UI 套件邊界。
2. 以可擴充的宣告式狀態轉移表與注入的動作處理器，取代 Access8Graph
   物件導向的 State 類別階層。

本工作分成五個里程碑。每個里程碑都必須能獨立審閱及驗證，完成後才能進入下一個。

## 已定案事項

本設計不重新討論下列決策：

- 本工作維持單一總設計，每個里程碑各有獨立章節。
- `NavigationCommand` 採用 `StrEnum`。
- `NavigationStateId` 採用 `StrEnum`，並列出所有合法的導航狀態。
- 每一條轉移規則都有固定的目標狀態。
- 依資料決定的分支使用多條含 guard 的規則表達，不由 action 選擇目標。
- guard 只能純讀取單次規則評估共用的 immutable snapshot。
- 禁止規則優先順序。同一來源狀態與命令最多只能有一個 guard 成立。
- action handler 完成所有可能失敗的驗證後，可以直接修改既有 navigator。
- action 成功後，engine 才提交目標狀態。
- 未預期的 action 例外會停止導航工作階段；不導入 rollback 機制。
- 自動前進以內部 `NavigationCommand.AUTO` 表達。
- 狀態進入處理器可以建立 view 與 presentation data，但不得變更狀態。
- 新舊 flow 會先在測試中比較，再一次完成 production 原子切換。
- 最終狀態不保留 command dictionary、舊 flow、import 或 speech settings
  compatibility facade。

## 現況

`refactor4.md` 所述重構已大致完成：

- Access8Graph 圖檔選擇與 flow lifecycle 已拆成獨立 use case。
- Access8Graph 按鍵轉譯與命令派送已有明確邊界。
- speech settings 已作為獨立 facade 傳入 UI。
- `application.output.Manager` 已退場。
- `application.keyboard` 正在移至 `application.input`。

剩餘的邊界問題如下：

- `SpeechEngineConfigStore` 位於 application code，卻直接執行 JSON 與檔案系統 I/O。
- `SpeechServiceProtocol` 迫使 consumer 依賴包含 17 個 method 的介面。
- 只有 NVDA Remote 使用的 state types 位於共用 application root。
- wx 專用的 shell、tray 與 panel 類別位於 `apps/shared`。
- 已過時的 speech settings alias 仍讓同一個 facade 有多個名稱。

目前主要架構問題是 `src/apps/access8graph/flow.py`：

- 同時包含 flow、基礎 state、20 個具體 state 與 view classes
- state 可直接修改完整 flow 與 navigator
- transition 是分散在 state method 內的隱性指定
- command 是透過 `getattr` 派送的任意 dictionary value
- state entry 可能觸發額外的隱性 transition
- output policy 與 transition execution 互相耦合

## 非目標

本階段不會：

- 變更 speech settings JSON schema
- 變更 UI 行為或版面
- 重寫 GraphML parser、model 或 navigator
- 重新設計 bootstrap provider
- 重構 scheduler concurrency
- 建立整個 repository 共用的通用 state-machine framework
- 將 Key Echo 或 NVDA Remote 遷移到新的 transition engine
- 在 parity 工作中刻意修正既有 Access8Graph 行為
- 在里程碑完成後保留舊 import path

## 目標架構

### 套件邊界

目標套件歸屬如下：

```text
application/
  input/
    service.py
  output/
    speech/
      settings_store.py       # SpeechSettingsStore port
    ports.py                  # narrow speech protocols

adapters/
  config/
    json_speech_settings.py   # JsonSpeechSettingsStore adapter

apps/
  nvda_remote/
    state.py
  shared/
    mode_manager.py
    speech_runtime_settings.py
    speech_settings_facade.py

ui/
  shared/
    panel_controller.py
    tool_app_shell.py
    tray_icon.py
```

consumer 遷移完成後，刪除 `application/config.py`、`application/state.py`、speech
compatibility modules，以及 `apps/shared` 下的舊 UI modules。

### 語音 Ports

依 consumer 角色拆分過大的語音介面：

```python
class SpeechOutputPort(Protocol):
    def speak(self, sequence: SpeechSequence) -> None: ...
    def cancel(self) -> None: ...
    def pause(self, is_paused: bool) -> None: ...


class SpeechSettingsPort(Protocol):
    def get_engine_options(self) -> tuple[tuple[str, str], ...]: ...
    def get_selected_engine(self) -> str: ...
    def set_engine(self, engine_id: str) -> None: ...
    def list_voices(self) -> tuple[tuple[str, str], ...]: ...
    def get_voice(self) -> str | None: ...
    def set_voice(self, voice_id: str) -> None: ...
    def get_rate(self) -> int | None: ...
    def set_rate(self, value: int) -> None: ...
    def get_pitch(self) -> int | None: ...
    def set_pitch(self, value: int) -> None: ...
    def get_volume(self) -> int | None: ...
    def set_volume(self, value: int) -> None: ...
    def get_supported_numeric_settings(
        self,
    ) -> tuple[SpeechNumericSetting, ...]: ...


class SpeechLifecyclePort(Protocol):
    def shutdown(self) -> None: ...


class SpeechServicePort(
    SpeechOutputPort,
    SpeechSettingsPort,
    SpeechLifecyclePort,
    Protocol,
):
    pass
```

具體 speech service 繼續透過 structural typing 滿足這些契約。consumer 只宣告自己
使用的最小契約。`SpeechServicePort` 只供確實需要所有能力的 composition point
使用。

### 語音設定持久化

`SpeechSettingsStore` 保留目前的 store operations：

- 載入／儲存所選 engine
- 依 engine 載入／儲存 voice
- 依 engine 與 setting ID 載入／儲存 numeric setting

`JsonSpeechSettingsStore` 保留下列行為：

- 現有 JSON keys 與巢狀結構
- UTF-8 編碼
- 建立上層目錄
- 限制 numeric settings 範圍
- 檔案不存在、格式錯誤或無法讀取時，回復空資料／預設值

`SpeechRuntimeSettingsCoordinator` 只依賴 `SpeechSettingsStore`。app entrypoint
負責建立 JSON adapter。

## Access8Graph 轉移模型

### 命令

`NavigationCommand` 是封閉的 `StrEnum`，包含目前所有外部 domain commands 與一個
內部命令：

```text
UP
DOWN
LEFT
RIGHT
CONFIRM
HOME
END
SELECT_DIRECTION
SELECT_UNDIRECTED
SELECT_PLAN
QUIT
OPEN_HELP
OPEN_MODE
OPEN_BROWSER
SELECT_STATION
SELECT_LINE
SELECT_ENDPOINT
AUTO
```

- HID 專用名稱不進入 domain enum
- 只有 keyboard translator 能將 HID event 轉成 command
- 只有 transition flow 能產生 `AUTO`
- 沒有實際 domain 需求前，不新增 payload fields

`ESCAPE` 仍是外層 navigation-mode command，由 `ModeManager` 在 event 到達
transition flow 前處理。它不是 `NavigationCommand`。

### 狀態 ID

`NavigationStateId` 是封閉的 `StrEnum`，涵蓋既有 state set：

```text
MODE
STATIONS
LINES
DIRECTION_END_POINT
DIRECTION_RUN
UNDIRECTION_RUN
PLAN_RUN
DIRECTION_TRANSFER
UNDIRECTION_TRANSFER
EXPLORE_NEIGHBOR
EXPLORE_SUB_LINE
DIRECTION_STATIONS
DIRECTION_LINES
SOURCE_STATIONS
SOURCE_LINES
DESTINATION_STATIONS
DESTINATION_LINES
UNDIRECTION_STATIONS
UNDIRECTION_LINES
UNDIRECTION_SUB_LINES
HELP
```

`HELP` 取代目前動態建立的 `HelpState` identity。return state 仍是
`NavigationContext` 內的資料。

transition、context、test 與 action handler 都不得使用任意 state 字串。

### Immutable Snapshot

engine 在評估一組來源狀態與命令的候選規則前，只建立一份
`NavigationSnapshot`。它是 frozen value object，只包含 guard 所需的 facts，例如：

- current state 與 return state
- 目前的 view selection 與 option count
- selected navigation mode
- line、station、source 或 destination 是否存在
- neighbor 與 transfer counts
- navigator run 是否 active

同一次評估的所有 guard 都收到相同 snapshot。guard：

- 只能讀取 snapshot
- 不得取得 mutable context 或 navigator
- 不得執行 I/O
- 不得修改 cache 或 registry

transition 成功後，engine 會先建立新的 snapshot，再評估 `AUTO`。

### 轉移規則

transition rule 是 immutable，包含：

```python
@dataclass(frozen=True, slots=True)
class TransitionRule:
    source: NavigationStateId
    command: NavigationCommand
    target: NavigationStateId
    action_id: ActionId
    guard_id: GuardId | None = None
```

每一條規則只有一個固定 target。不使用 `allowed_targets`、dynamic target 或
`ActionResult.target_state`。

對同一組 source 與 command：

- 只有在不存在 guarded alternatives 時，才能有一條 unguarded rule
- 多條規則必須使用互斥的 guards
- 沒有 guard 成立是一般 rejection
- 多個 guard 成立時拋出 `AmbiguousTransitionError`
- list order 不得作為 rule priority

### 轉移引擎

engine 將一個 external command 當作一個 macrostep 執行：

1. 建立一份 immutable snapshot。
2. 找出符合 current state 與 command 的所有規則。
3. 以相同 snapshot 評估所有候選 guard。
4. 沒有規則成立時回傳 rejected。
5. 多條規則成立時拋出 `AmbiguousTransitionError`。
6. 呼叫所選的 action handler。
7. action 拒絕時保留 current state。
8. action 成功時，執行 source-state exit presentation processing。
9. 提交規則的固定 target。
10. 執行 target-state entry processing，建立 view 與 presentation effects。
11. 建立新的 snapshot 並評估 `AUTO`。
12. 重複 automatic transitions，直到狀態穩定。
13. 整個 macrostep 只呈現一次累積結果。

engine 不會：

- 知道 HID values
- 呼叫 wx
- 直接 speak、cancel 或 beep
- 透過 `getattr` 派送 handler
- 透過 action result 選擇 target
- 捕捉並隱藏未預期的 action exception

### 自動轉移

automatic transition 是使用 `NavigationCommand.AUTO` 的一般固定目標規則。

它取代目前由 state `enter()` 觸發的隱性 transition，包括只有單一選項時的自動
選擇。state-entry handler 可以：

- 建立 current view
- 將 open message 與 hint 加入 presentation effects
- 提供下一份 snapshot 所需的 facts

它們不得變更 `NavigationContext.current_state`。

source-state exit handler 可以在提交 target 前加入 close message。entry 與 exit
handler 都不得選擇其他 target 或執行 output I/O。

engine 透過下列機制保護 automatic processing：

- 每個 macrostep 最多執行 32 次 automatic transitions
- 在 current macrostep 追蹤 visited rule/state
- 重複或用盡次數時拋出 `AutomaticTransitionCycleError`

### 動作處理器

handler 透過 action registry 注入，並以 typed action ID 定址。handler 接收：

- 用來選擇規則的 immutable snapshot
- 窄介面的 mutable navigation context
- 該 action 實際需要的 navigator collaborator

handler：

- 在可行情況下，先完成所有可能失敗的 query 與 validation，再進行 mutation
- 可以直接修改既有 navigator
- 回傳 accepted 或 rejected，以及 presentation/context effects
- 不得選擇或提交 target state
- 不得 speak 或 beep

本設計不導入 copy-on-write 或 rollback。未預期的 exception 是 fatal
navigation-session error。

### Context

`NavigationContext` 擁有 state-machine session data，而非 infrastructure：

- current state
- return/background state
- current view model
- selected navigation mode
- pending presentation effects
- navigator 尚未擁有的 state-machine selection data

它不擁有：

- output adapters
- HID events
- wx objects
- transition table 或 registries

### 狀態 Lifecycle Handlers

state lifecycle handlers 與 transition actions 分開注入：

- exit handler 提供 source-state close effects
- entry handler 建立 target view，並提供 open/hint effects
- 兩者都不得變更 current state
- 兩者都不得執行 output
- entry processing 必須在建立下一份 `AUTO` snapshot 前完成

這能讓 lifecycle presentation 保持明確，同時不允許隱性 transition。

### 呈現

`FlowPresenter` 接收一個完成的 macrostep result 與窄介面的 `FlowOutput` port。它保留
目前可觀察到的順序：

1. close messages
2. open messages
3. 適用時的首次進入 hint
4. current view display

接著只對穩定狀態執行一次現有的 cancel-and-speak policy。

current state 拒絕已識別的 command 時，保留目前的 beep 與 current-view speech
行為。無法識別的 HID event 保留目前 navigation mode 的 consume behavior，且不
進入 transition engine。

action 拋出未預期例外時，不輸出部分完成的 presentation。

## 狀態轉移表驗證

`TransitionTableValidator` 在測試及 flow 組裝時執行，並拒絕：

- 未知的 command、state、action 或 guard ID
- 重複的 unguarded rules
- 相同 source 與 command 同時存在 unguarded rule 與 guarded alternatives
- 無法到達的 non-terminal states
- 無效的 initial state
- help/menu states 缺少必要 return path
- 可由靜態分析發現的 `AUTO` cycles

guard overlap 取決於資料，因此也必須在 runtime 檢查。測試必須為每個 guarded
branch 提供代表性 snapshots，並證明每個預期分支恰好只有一條規則成立。

navigation-mode exit behavior 由 ModeManager/service integration tests 驗證，不由
transition table 驗證。

## 錯誤語意

可預期的 outcomes 不使用 exception：

- `TRANSITIONED`：action 成功，且 target 與 source 不同
- `HANDLED`：action 成功，但留在相同 state
- `REJECTED`：沒有 guard 成立或 action 拒絕
- `UNHANDLED`：保留給 flow contract 以外的 command

未預期的錯誤包括：

- ambiguous transitions
- automatic-transition cycles
- 組裝驗證未攔截到的 missing registry entry
- 未預期的 action 或 navigator exceptions

未預期錯誤會傳遞到既有 app-service boundary。該 boundary 會送出
`ErrorRaised`、停止 navigation，並保留既有 error speech 行為。

## 里程碑 1：低風險邊界與相容層清理

### 意圖

在 transition rewrite 前修正 package ownership、縮小 speech dependencies，並移除
過時 alias。

### 範圍

- 完成 keyboard service 移至 `application.input`
- 導入窄 speech ports
- 導入 speech settings store port 與 JSON adapter
- 遷移所有 runtime 與 test consumers
- 將 NVDA Remote state 移至其 app package
- 將 wx shell classes 移至 `ui/shared`
- 移除 speech-settings compatibility aliases

### 必要終態

- 刪除 `src/application/keyboard.py`
- 刪除 `src/application/config.py`
- 刪除 `src/application/state.py`
- 刪除 `src/apps/shared/speech_settings_controller.py`
- 刪除 app-specific speech-settings alias modules
- 刪除 `apps/shared` 下的舊 wx modules
- 不 re-export 舊 path

### 行為限制

- speech settings persistence 維持 byte-for-byte schema compatibility
- malformed configuration fallback 保持不變
- speech engine、voice、rate、pitch 與 volume 行為保持不變
- UI startup、tray、panel 與 shutdown 行為保持不變
- NVDA Remote connection/control state 行為保持不變

### 驗證

- 每個 public import 移動時同步調整 focused tests
- JSON adapter contract tests 涵蓋既有 read/write 與 corruption behavior
- protocol tests 證明具體 speech services 滿足所需 ports
- repository search 找不到舊 imports
- 完整 unit 與 integration suite 通過

## 里程碑 2：既有 Flow 行為基準

### 意圖

在實作替代方案前，先將目前的隱性行為明文化。

### 範圍

建立 data-driven characterization matrix，涵蓋每一個既有 state：

- state entry 與 exit effects
- primary commands
- rejected recognized commands
- target state
- view data 與 selection
- navigator mutations
- message、hint 與 display ordering
- beep behavior
- background/return behavior
- single-option automatic progression
- help、transfer、exploration 與 route-planning paths

### 規則

- 本里程碑不修改 production code
- 發現的 bug 另行記錄
- 即使現有行為不理想，測試仍描述現況
- 每個 scenario 都必須辨識所有 externally observable effects

### 完成定義

- matrix 包含每個既有 concrete state
- 現有 `if/elif/else` transition logic 的所有 branches 都有對應案例
- automatic transitions 明確表示成預期的 chained steps
- baseline suite 對既有 flow 測試通過

## 里程碑 3：平行轉移引擎

### 意圖

在不混入 production path 的情況下，於測試後方建立完整替代方案。

### 初始檔案結構

```text
src/apps/access8graph/navigation/
  __init__.py
  model.py
  snapshot.py
  engine.py
  actions.py
  table.py
  presenter.py
  flow.py
```

初始 modules 依責任維持集中。等到里程碑 5 契約穩定後，再依 mode family 拆分。

### 範圍

- 實作 command 與 state enums
- 實作 snapshots 與 pure guards
- 實作 rules、validation 與 engine macrosteps
- 實作 action 與 guard registries
- 實作 `AUTO` processing 與 cycle protection
- 實作 context、view models、results 與 presenter
- 實作完整 declarative transition table
- 實作符合 dispatcher boundary 的新 flow adapter

### Parity 方法

以里程碑 2 的相同 scenarios 測試：

- 舊 `MrtFlow`
- 新 transition flow

parity 比較：

- final state
- intermediate automatic steps
- navigator mutation
- view model
- messages、hints 與 speech item order
- cancel/speak/beep calls
- rejection 與 exception behavior

### 完成定義

- 每個 baseline scenario 對兩種實作都通過
- transition table validation 通過
- ambiguous guard tests 依設計失敗
- 已測試 guard purity 與 shared-snapshot usage
- production 仍只建立舊 flow

## 里程碑 4：原子切換與舊架構移除

### 意圖

將 production 切換至已驗證的 transition engine，並在同一里程碑移除舊架構。

### 範圍

- 讓 `MrtFlowFactory` 建立新 flow
- 讓 translator 回傳 `NavigationCommand`
- 讓 dispatcher 依賴 typed `NavigationFlow` contract
- 將 result mapping 切換至 `TransitionResult`
- 移除舊 state 與 view classes
- 移除 command dictionaries 與 dynamic `getattr` dispatch
- 移除不再需要的暫時性新舊 parity fixtures

### 限制

- 不使用 feature flag
- runtime 不 fallback 至舊 flow
- 不使用 compatibility adapter
- 不重寫 GraphML model 或 navigator

### 完成定義

- 不再有舊 hierarchy 的 runtime reference
- 不再有 Access8Graph command dictionary
- key-event-to-output integration paths 通過
- startup、hotkey、stop 與 unexpected-error 行為保持不變
- 所有 unit 與 integration tests 通過

## 里程碑 5：模組收斂與完整性保護

### 意圖

在 engine contract 穩定後改善 ownership，並讓後續 table 擴充維持安全。

### 目標分組

依下列 concern 拆分 actions 與 transition tables：

- common/list/help
- mode selection
- direction exploration
- undirected exploration
- route planning
- transfer/explore

所有 groups 組裝成一份經完整驗證的 transition graph。

### 範圍

- 依 navigation concern 拆分已穩定的 action 與 table modules
- 保持 engine 與 shared model 不依賴 mode-family details
- 新增 negative validation suites
- 說明如何新增 command、guard、action、state 與 transition
- 更新 module ownership 文件

### 必要負向測試

- duplicate rules
- unguarded 與 guarded rule conflicts
- multiple successful guards
- unknown action 或 guard
- unreachable states
- invalid initial state
- missing help/menu return
- missing required in-flow return behavior
- automatic-transition cycles 與 maximum-step exhaustion

### 完成定義

- 新增 rule 或 state 不需修改 engine
- 每個 family module 只有一項 navigation concern
- 所有 tables 組成一份有效 graph
- extension 文件符合實際契約
- 完整 test suite 通過

## 測試策略

測試由最小契約向外進行：

1. command、state、snapshot、rule 與 result 的 value-object tests。
2. graph 與 registry integrity 的 validator tests。
3. 使用 fake guard 與 action 的 engine tests。
4. 使用 fake context 與 navigator 的 action tests。
5. 驗證精確輸出順序的 presenter tests。
6. characterization 與新舊 parity scenarios。
7. dispatcher 與 service integration tests。
8. 完整 unit 與 integration regression suite。

測試必須特別證明：

- candidate guards 共用同一個 snapshot instance
- guard 無法透過契約存取 mutable context
- action rejection 不提交 state
- action exception 不提交 target state，也不輸出 partial presentation
- state entry 無法變更 state
- automatic transitions 在穩定後只呈現一次
- runtime 絕不依 rule order 解決 ambiguity

## 風險與控制

### 遺漏隱性行為

控制方式：實作替代方案前先完成里程碑 2，並讓每個 scenario 對兩種 flow 執行。

### 部分 Navigator Mutation

控制方式：mutation 前先驗證、保持 action 聚焦、未預期失敗時停止整個 session，並為
transfer 與 route actions 加入 before/after assertions。

### 語音順序回歸

控制方式：比較完整且有順序的 speech items 與 output calls，而不只比較 final
state。

### 過度抽象

控制方式：engine 先保留在 `apps/access8graph`；出現第二個具體 consumer 前，不抽成
shared framework。

### 同時變更過多

控制方式：完成並驗證每個里程碑後，才能開始下一個。不得將 GraphML、scheduler、
bootstrap 或 UI behavior changes 混入本工作。

## 整體完成定義

只有符合下列所有條件，本階段才算完成：

- package ownership 符合本設計
- obsolete compatibility paths 已移除
- application policy 依賴 speech store port，而不是 JSON I/O
- speech consumers 使用符合需求的窄 protocols
- Access8Graph commands 與 states 是封閉的 typed enums
- 所有 branches 使用固定目標的 declarative rules
- guards 是 pure，且評估同一份 immutable snapshot
- ambiguity 會被拒絕，而不是依 priority 解決
- automatic transitions 使用 `NavigationCommand.AUTO`
- actions 無法選擇或提交 target state
- 每個穩定 macrostep 只執行一次 presentation
- 舊 State hierarchy 與 dynamic dispatch 已移除
- 使用者可見的 navigation、speech、beep、hotkey 與 error 行為維持相容
- 所有 unit 與 integration tests 通過
