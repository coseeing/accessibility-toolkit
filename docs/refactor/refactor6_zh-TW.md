# 架構審查 v6

## 以 Design Patterns 與 SOLID Principles 檢視 `src/`

## 1. 審查目標

本文件從兩個角度檢視目前的 `src/` 程式碼：

- **Design Patterns**：目前哪些地方已經採用了有價值的架構模式
- **SOLID Principles**：這些模式目前在哪些地方仍留下職責過重、介面過寬、
  或依賴方向不夠清楚的問題

重點不是要主張 pattern 不好，而是要指出：

> 某個 pattern 雖然存在，但它目前的封裝方式仍然削弱了 SRP、ISP、OCP 或
> DIP

本文件聚焦在 **refactor 建議**，不是單純列出一般性的 code smell 清單。

## 2. 整體判斷

這個 codebase 的架構狀態，已經比前幾輪 refactor 明顯改善。幾個重要 pattern
其實已經用對了：

- app service 扮演 facade
- Access8Graph 採用 table-driven state machine
- output 與 settings 行為改用 Protocol 型別的 ports
- bootstrap 比以前承擔更多 composition 責任
- protocol events 比 earlier iterations 更 typed

目前主要的問題不是「缺少 pattern」。
而是：

> 某些已經成功導入的 pattern，其周邊支撐模組又累積了過多責任

換句話說：

- pattern 的選擇通常是正確的
- 但 pattern 周圍的 ownership boundary 仍然不夠均衡

## 3. 哪些 Design Patterns 目前運作得不錯

### 3.1 app service 中的 Facade

`Access8GraphAppService`、`NvdaRemoteAppService` 與 `KeyEchoAppService`
現在確實扮演 UI-facing facade，而不再是早期那種一口氣吞下大量 business logic
的巨大類別。

這樣做的好處：

- UI code 只需要面對一個穩定的 entrypoint
- 底層 use cases 可以各自演進
- event 與 lifecycle orchestration 不再直接外溢到各處

對 SOLID 的意義：

- 這改善了 app boundary 上的 SRP
- 也幫助 DIP，因為 UI 依賴的是穩定的 application-facing surface

### 3.2 Access8Graph 的 Table-Driven State Machine

從舊版 state hierarchy 轉成：

- `navigation/model.py`
- `navigation/engine.py`
- `navigation/tables/`
- `navigation/actions/`

這是一個很明顯的進步。

好處在於：

- transitions 變成顯式可見
- 可以在 runtime 前做 validation
- tests 可以直接驗證 rules 與 macrosteps
- 相較於舊的 `getattr` 驅動 state methods，OCP 更好

對 SOLID 的意義：

- OCP 獲得改善，因為新增 rule 是擴充 table，而不是修改隱晦的 state methods
- 舊版 `State` subclasses 間不一致造成的 LSP 問題，大多已被移除

### 3.3 output 與 persistence 中的 Strategy / Port 用法

目前程式碼已經把下列邊界改成 Protocol：

- speech output
- speech settings
- speech lifecycle
- settings persistence

這個方向是對的。

好處在於：

- application policy 可以依賴行為契約
- adapters 可以被替換
- tests 很容易用 structural fake 來模擬

對 SOLID 的意義：

- DIP 比 earlier refactor stages 好很多
- ISP 也有改善，雖然不是所有 consumer 都已完整利用這些細分後的 ports

## 4. 哪些地方是 Pattern 與 SOLID 仍在拉扯

### 4.1 `navigation/actions/common.py`

#### 從 Pattern 角度看

這個模組是 table-driven state machine 的支撐核心，集中放了 shared
actions、guards、IDs、entry effects 與一些 helper objects。

#### 從 SOLID 角度看

它現在已經大到不能再算是單一責任。

目前內容包括：

- view models
- action IDs
- guard IDs
- action implementations
- guard implementations
- entry/exit presentation effects
- snapshot assembly support

即使外圍 pattern 是正確的，這裡仍然是明顯的 SRP 違反。

#### 建議

應依責任來拆，而不是只看行數：

- 先把 `ListViewModel` 與 `RunViewModel` 移出
- 把 ID definitions 和 behavioral functions 分開
- `common actions` 只保留真正跨 family 共用的部分

### 4.2 `MrtFlowFactory` 與 `Access8GraphNavigationSession`

#### 從 Pattern 角度看

這一帶其實已經用了 Factory 與 Session-style orchestration。

#### 從 SOLID 角度看

目前 factory 同時負責：

- graph 載入
- model 建構
- navigator 建構
- registry 組裝
- output adapter 組裝
- flow 啟動

目前 session 同時負責：

- selected graph 依賴
- active flag
- flow lifecycle
- output cancellation side effect
- status notification

這些責任雖然還可控，但 composition boundary 仍然偏厚。

#### 建議

把 assembly 與 runtime lifecycle 分開：

- 一個 builder/composition 單元負責組 flow
- 一個 session 單元只負責 start/stop/active state

保留原本的 pattern，但把每個類別的角色收窄。

### 4.3 `Capabilities` 作為偏寬的 dependency bag

#### 從 Pattern 角度看

`Capabilities` 是一個方便的 composition object。

#### 從 SOLID 角度看

在更深的層次，它有點像小型 service locator：

- consumers 拿到的東西比實際需要的多
- 已經拆好的 narrow ports 價值被稀釋
- ISP 與 DIP 的收益被部分抵消

這不是致命問題，但確實是結構上的阻力。

#### 建議

如果要保留 `Capabilities`，最好只放在 bootstrap 附近。
更底層則優先改成明確的 constructor dependencies 搭配 narrow ports。

### 4.4 `QueuedService` 作為 Decorator/Proxy

#### 從 Pattern 角度看

`QueuedService` 本質上是包住 `SpeechService` 的 decorator 或 proxy。

#### 從 SOLID 角度看

它現在混合了：

- queueing policy
- output routing
- settings pass-through
- lifecycle shutdown

這個 pattern 本身是看得出來的，但被裝飾的 surface 太寬。

這是典型的「pattern 有了，但 ISP 與 SRP 仍偏弱」的情況。

#### 建議

保留 decorator 的想法，但把被裝飾的責任收窄：

- 只裝飾 speech output behavior
- 不要讓 queueing layer 預設就接管整個 settings API

### 4.5 app-service 模組中的 inline mode classes

#### 從 Pattern 角度看

目前程式碼透過 `ModeManager` 搭配具體 mode objects，形成一個小型的 Mode
pattern。

#### 從 SOLID 角度看

但這些 concrete mode objects 仍嵌在 service 模組裡：

- `Access8GraphNavigationMode`
- `RemoteControlMode`

這讓 mode pattern 雖然存在，卻仍部分隱藏在 facade implementation 裡。

#### 建議

把 mode implementations 提升到獨立模組。
這是小改動，但可以讓實際檔案結構更符合已存在的 pattern。

### 4.6 navigation assembly 裡的 local `_OutputAdapter`

#### 從 Pattern 角度看

這是 Adapter pattern。

#### 從 SOLID 角度看

這個 adapter 是真的存在，但它目前是匿名且 local 的。這通常表示該 boundary
在架構上是真的，只是還沒有被賦予穩定的歸屬位置。

#### 建議

要嘛：

- 把它提升成具名 adapter 模組

要嘛：

- 把這段行為收回真正擁有該 boundary 的 output 類別裡

如果一個重要 adapter boundary 不只是一時性的實驗，就不應長期躲在區域 helper
裡。

## 5. 以 SOLID 原則整理的摘要

### SRP

改善的地方：

- app services 比 earlier versions 聚焦許多
- Access8Graph transitions 不再混在舊版 state hierarchy 中

仍有壓力的地方：

- `navigation/actions/common.py`
- `apps/access8graph/use_cases/navigation.py`
- `application/output/service.py`

### OCP

改善的地方：

- transition rules 透過 table registration 更容易擴充
- ports 讓 adapters 更容易新增

仍有壓力的地方：

- 大型 shared modules 仍然讓不相關的新需求需要去修改 central files
- `common.py` 有風險變成所有新 navigation behavior 都得碰的地方

### LSP

改善的地方：

- 舊版脆弱的 state subclass 假設大多已被移除

仍有壓力的地方：

- 目前看不出明顯的 subtype defect
- 現階段 LSP 風險低於 SRP、ISP、DIP

### ISP

改善的地方：

- speech ports 已拆分

仍有壓力的地方：

- 很多 consumers 仍拿到偏寬的 collaborators
- `QueuedService` 仍暴露一個過大的合成 surface
- `Capabilities` 仍鼓勵寬於所需的依賴

### DIP

改善的地方：

- settings persistence 與 speech behavior 已有更清楚的 ports

仍有壓力的地方：

- 較深層仍接收 concrete aggregation objects
- 某些 assembly 與 adapter boundaries 還是以 local 形式存在，而不是穩定抽象

## 6. Refactor 建議

## 6.1 短期可獨立交付的 slices

### 建議 1

把 Access8Graph navigation assembly 從
`src/apps/access8graph/use_cases/navigation.py` 拆出去。

原因：

- 在 SRP 改善與低風險之間取得最好平衡
- 可以直接承接已完成的 transition-engine 工作

### 建議 2

拆分 `src/apps/access8graph/navigation/actions/common.py`，第一步先從
view-model classes 開始。

原因：

- 這是目前新 navigation stack 中最大的責任集中點
- 可讀性提升很大，行為風險卻低

### 建議 3

把 concrete mode classes 從 app-service 模組搬出去。

原因：

- 讓程式碼結構更符合既有的 Mode pattern
- 屬於小型、機械式、容易驗證的重構

### 建議 4

如果某些 local adapters 對應的 boundary 已經穩定，就把它們改成具名的
module-level adapters。

原因：

- 讓真正的架構接縫變得可見且可重用

### 建議 5

逐個 app 開始，慢慢把依賴從偏寬的 `Capabilities` 收窄。

原因：

- 可以真正發揮已存在 ports 的價值
- 逐步降低跨 app constructor coupling

## 6.2 高價值但較大的主題

### 主題 1. 以 family 為中心重整 Access8Graph navigation modules

把各 navigation family 的 rules、actions、entry behavior 與 view concerns
收得更緊，讓 `common.py` 不再像第二個隱藏核心。

### 主題 2. 以更窄的 decorators 重整 output stack

重新設計 `QueuedService` 與相關 composition，讓 queueing、settings 與
lifecycle 成為刻意分開的角色，而不是由一個大量 pass-through 的物件承擔。

### 主題 3. 用明確的 composition contracts 取代 capability bags

讓 repo 更往「明確的 app constructor dependencies」前進，而不是倚賴泛用的
aggregate collaborators。

## 7. 最終建議

從 **Design Patterns vs SOLID Principles** 的角度來看，這個 codebase
現在不需要再引進新的 grand pattern。

真正需要的是：

1. 保留已經選對的 patterns
2. 減少這些 patterns 周邊重新累積的責任集中
3. 讓 narrow ports 與 explicit composition 不只存在於 protocol definitions，
   也真正落到 consumer code 裡

如果下一步只能選一個 refactor，應優先選：

> 拆出 Access8Graph navigation assembly

如果緊接著再做第二個 refactor，則應選：

> 拆分 `navigation/actions/common.py`，並從 view models 開始
