# 架構重構檢視 v4

Context
-------
這份檢視是拿 `docs/refactor/refactor3.md` 對照目前的程式碼庫。

自 `refactor3.md` 之後，程式碼庫已經完成當時建議下一步中的大部分重構切片：

- 共用的語音執行階段設定串接已存在於
  `src/apps/shared/speech_runtime_settings.py`
- 應用程式入口現在改用共用 coordinator，不再在各處重複語音設定
  持久化邏輯
- 型別化的 protocol events 已經落到 NVDA Remote 的 protocol/session 層
- `NvdaRemoteAppService` 不再是把原始 protocol 狀態字典轉成 UI 可用事件
  的中心位置
- NVDA Remote 的 orchestration 已經拆成較聚焦的 use case，例如：
  - `RemoteConnectionUseCase`
  - `RemoteProtocolEventHandler`
  - `RemoteStatusPresenter`
  - 既有的 control/input-forwarding use cases

因此，下一輪重構不應再把 NVDA Remote 當成主要的架構瓶頸。那部分現在
多半屬於「收尾與穩定」的工作。

接下來的階段應該改把重點放在那些邊界還不完整、或抽象價值還不夠清楚的
部分。

v3 之後的變化
---------------------

1. 共用的語音執行階段設定，現在已經是跨應用問題的解答。

`refactor3.md` 指出三個應用入口在 speech engine/voice/rate/pitch/volume
啟動串接上有重複。這些重複現在已經集中到
`SpeechRuntimeSettingsCoordinator`。

目前評估：
- 這不再是主要重構目標。
- 入口之間剩下的差異，多半是各 app 合理的執行階段政策，而不是偶發的
  重複。

2. NVDA Remote 不再是最急迫的服務邊界問題。

`refactor3.md` 優先處理 NVDA Remote 的型別化 protocol events 與服務拆分。
目前程式碼已經反映出這個切分：

- `RemoteSession` 和 `MessageRouter` 在 app 邊界上看起來已經不是 dict-first
  的做法
- `NvdaRemoteAppService` 透過聚焦的 use case 組合，而不是直接包辦所有
  connection/protocol/presentation 邏輯
- protocol event handling 和 connection lifecycle 已經有實質分離

目前評估：
- NVDA Remote 還是需要一般性的整理與測試維護。
- 但它已經不是下一輪最值得投入的大型重構點。

3. 剩下的架構不平衡，在 Access8Graph 上更明顯了。

在 bootstrap extraction、語音執行階段設定、typed events，以及 NVDA Remote
orchestration 都有明顯改善之後，目前剩下最大的「service 同時扮演
controller、workflow owner、lifecycle owner」的形狀，已經出現在
`Access8GraphAppService`。

目前評估：
- 這已經是和前面重構方向相比最明顯還沒對齊的地方。
- 它夠局部，能安全改善；也夠大，值得成為下一個主軸。

4. 有些共用 / controller 抽象仍然把政策與持久化知識綁在一起。

現在的執行階段組裝比以前好，但 UI-facing controller methods、
持久化 callbacks、以及 app-service-level policy 之間的界線仍然有點混在一起。

主要例子是：
- `src/apps/shared/speech_settings_controller.py`
- app service 裡的 speech-setting pass-through methods

目前評估：
- 這不是壞掉，但它仍然讓 service 的對外面積偏大。
- 在 Access8Graph service 拆分之後，再處理這塊會比較合適。

5. `application.output.Manager` 現在看起來更像過渡性抽象。

目前的 active architecture 是以這些為中心：
- `Capabilities`
- `QueuedService`
- speech runtime services
- 直接的 router callbacks

`application.output.Manager` 雖然還存在，而且也有測試，但它的泛用名稱
已經不太符合它現在較窄的角色。

目前評估：
- 這件事的優先序仍然低於 app-service boundary 的工作。
- 但這個抽象現在應該要嘛講清楚，要嘛退場，不宜繼續保持模糊。

目前最高槓桿的重構方向
--------------------------------------------

1. 把 Access8Graph 提升到和 NVDA Remote、Key Echo 一樣的 facade/use-case
   標準。

為什麼這現在是第一優先：
- `Access8GraphAppService` 仍然包辦檔案驗證、flow lifecycle、navigation
  state、hotkey startup policy、錯誤語音 side effect、以及 speech-settings
  pass-through。
- `Access8GraphNavigationMode` 仍然會碰 private service methods。
- translator 建立與 command execution 仍然跟 mode handling 綁在一起，而不是
  有穩定的邊界。

為什麼這重要：
- 它讓一個 app 落後於已經在其他地方建立好的架構標準。
- workflow、state、UI-facing methods 混在一起，讓局部修改更難。
- 私有方法耦合會讓後續重用與測試都更痛苦。

建議方向：
- 保持 `Access8GraphAppService` 作為 UI-facing facade
- 抽出聚焦的單元，分別處理：
  - graph selection 與驗證
  - flow 建立 / 銷毀
  - navigation session lifecycle
  - command translation / dispatch
  - hotkey-start policy 與啟動錯誤回報
- 移除 mode 到 private service 的耦合

2. 收斂共用 speech settings 的邊界。

為什麼這是第二優先：
- app services 目前還直接暴露很多 speech pass-through methods
- `SpeechSettingsController` 把 speech adapter calls 和持久化 callbacks 混在一起
- 目前做法是可用的，但還是會讓 app services 傾向變成「什麼都管」的
  controller facade

為什麼這重要：
- 它擴大了每個 app service 的公開面
- 讓 speech settings 在每個 app service 裡都變成重複的 UI-facing concern
- 讓人不容易看出 speech settings 究竟是 app-service 行為，還是共享的
  feature-module 行為

建議方向：
- 決定 speech settings 要維持為：
  - 由每個 app service 擁有的 shared controller，或
  - 另外提供給 UI code 的 dedicated shared facade/module
- 如果仍留在 app services 裡，至少要透過更明確的 shared protocol /
  mixin / facade boundary 來減少重複

3. 在模式已經開始出現的地方，標準化 command translation 邊界。

為什麼這不是第一，而是第三：
- 這個 repo 已經有可用的 input primitives，不需要再做一個大型 generic
  input pipeline refactor
- 但 translator 建立與 command execution 在不同 app 之間仍然不夠一致

為什麼這重要：
- 它會影響可測試性與局部清晰度
- 在 Access8Graph 拆開之後，這件事很可能會變得更單純

建議方向：
- 在有價值的地方定義一個小型 translator contract
- 先套用在 Access8Graph，因為那裡的 translator 建立還是 inline 的
- 不要做成大型框架；只標準化已經重複出現的那個邊界

4. 釐清 `application.output.Manager` 的角色。

為什麼這是第四：
- 它概念上有點模糊，但沒有阻擋目前的執行階段工作
- 跟 service-boundary 問題相比，它的風險較低

建議方向：
- 擇一處理：
  - 保留它作為 compatibility utility，並重新命名 / 文件化，使其角色更窄，
    或
  - 確認沒有任何 active runtime path 依賴之後將它移除
- 不要在沒有真實使用情境的情況下，把它擴成更泛用的抽象

建議的重構切片
---------------------------

切片 1. Access8Graph flow lifecycle 抽出
-----------------------------------------------

目標：
- 把 flow 建立 / 銷毀，以及 navigation session state 的擁有權，從
  `Access8GraphAppService` 移走

最可能涉及的檔案：
- `src/apps/access8graph/service.py`
- `src/apps/access8graph/flow.py`
- `src/apps/access8graph/output.py`
- `src/apps/access8graph/input.py`
- 以及可能新增的模組，例如：
  - `src/apps/access8graph/use_cases/navigation.py`
  - `src/apps/access8graph/use_cases/graph_selection.py`

目標形狀：
- `Access8GraphAppService` 把 start / stop 邏輯委派給 navigation use case
- flow 建立由獨立的 factory / builder 負責
- mode enter / exit 對接穩定的公開介面，而不是 private service methods

主要風險：
- start / stop 時序改變，可能影響現有的 speech cancellation 行為
- hotkey startup failure 的錯誤回報如果搬動了，可能會破壞目前語意

完成定義：
- `Access8GraphNavigationMode` 不再呼叫 private service methods
- flow 建立 / 銷毀不再直接寫在 app service 裡
- 選擇 graph、開始 navigation、停止 navigation、以及錯誤語音的現有行為
  保持不變

切片 2. Access8Graph command translation 邊界
--------------------------------------------------

目標：
- 把 command translation 與 command execution 從 inline mode logic 中移出

最可能涉及的檔案：
- `src/apps/access8graph/input.py`
- `src/apps/access8graph/service.py`
- `src/apps/access8graph/flow.py`

目標形狀：
- 有一個穩定的 translator 或 command-dispatch boundary
- `Access8GraphNavigationMode` 處理的是 mode 語意，不是 translator 的組裝
- command execution 透過更清楚的單元邊界來完成

主要風險：
- 對未知按鍵的行為出現細微變化
- 不小心改到 key 是被 consume 還是 pass through

完成定義：
- translator instantiation 不再嵌在 `handle_key_event()` 裡
- 測試會把 command translation 行為和 mode lifecycle 分開描述
- pass-through / handled 的行為維持穩定

切片 3. 收斂共用 speech settings facade
-------------------------------------------------

目標：
- 減少 app services 中重複的 speech-settings pass-through surfaces

最可能涉及的檔案：
- `src/apps/shared/speech_settings_controller.py`
- `src/apps/nvda_remote/service.py`
- `src/apps/key_echo/service.py`
- `src/apps/access8graph/service.py`
- 以及相關的 UI controller 呼叫點

目標形狀：
- speech settings 有更明確的 shared feature 邊界
- app services 要嘛：
  - 暴露更小的 speech-settings interface，或
  - 透過命名清楚的 shared facade 去委派

主要風險：
- UI code 可能目前依賴 controller method 的精確名稱
- 如果過度抽象，可能只會增加層次，卻沒有減少複雜度

完成定義：
- speech settings 行為仍然是跨 app 共用的
- app services 上重複的 boilerplate methods 被減少，或被隔離到更清楚的
  邊界後面
- UI 行為與持久化設定都維持不變

切片 4. Output manager 釐清或退場
---------------------------------------------------

目標：
- 消除 `application.output.Manager` 的角色模糊性

最可能涉及的檔案：
- `src/application/output/manager.py`
- `tests/unit/test_output_manager.py`
- 任何剩餘的 consumer

目標形狀：
- 要嘛清楚標示 / 重新命名為 compatibility-oriented
- 要嘛移除，並把剩餘用途併回更清楚的執行階段路徑

主要風險：
- 如果太早做，可能帶來不少改動，卻沒有實際效益
- 測試可能寫了仍有歷史兼容意義的行為

完成定義：
- 程式碼庫不再把 `Manager` 呈現為核心抽象，除非它真的就是核心抽象
- 維護者不用翻很多檔案，就能看出它到底是 active architecture 還是
  compatibility code

建議順序
---------------

下一階段的建議順序：

1. Access8Graph flow lifecycle 抽出
2. Access8Graph command translation 邊界整理
3. 收斂共用 speech settings facade
4. Output manager 釐清或退場

為什麼這樣排：
- 先處理目前最大的 app-service 邊界問題
- 先把下一輪重構限制在單一 app 內，再碰共用 controller surfaces
- 避免太早花力氣在低槓桿的概念性整理

不要先做的事
----------------------

1. 不要重新打開 bootstrap/runtime extraction。

那部分已經到位，不再是主要架構問題。

2. 不要引入一個完整的 generic input command framework。

目前的程式碼庫不需要在這裡再加一個大型抽象。它需要的是把剩下那個 app
拉到和其他 app 一樣的標準。

3. 不要現在就做更雄心勃勃的 output bus。

目前還看不出現在的 app 需求已經足以支撐更泛用的 multimodal output
architecture。

下一階段的完成定義
----------------------------------------------

當以下條件都達成時，下一階段就算完成：

- `Access8GraphAppService` 變成薄的 facade，不再包辦 flow 建立、
  navigation lifecycle、以及 mode-private workflow details
- `Access8GraphNavigationMode` 只依賴穩定的公開介面
- Access8Graph command translation 有更清楚、可測試的邊界
- speech settings exposure 被收斂，或被隔離在更明確的 shared boundary 後面
- `application.output.Manager` 的角色已經清楚釐清為 active architecture 或
  compatibility code

Summary
-------

和 `refactor3.md` 相比，這份程式碼庫已經完成了前一階段最重要的 NVDA
Remote 與共用執行階段清理，因此下一階段的重心也跟著改變了。

現在最好的下一步，不是繼續切 NVDA Remote，而是把 Access8Graph 拉到同樣的
架構標準，接著收斂共用 speech settings 邊界，最後釐清
`application.output.Manager` 是否還應該留在 active design 裡。
