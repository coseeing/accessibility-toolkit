src/ 的 SOLID 檢視
===================

目標脈絡
--------
長期目標是建立一套可供上層應用重複使用的輸入 / 輸出基礎架構，特別是：
- 輸入：keyboard hook，以及未來其他輸入裝置或 hotkey
- 輸出：speech、tones、wave / 音效、braille
- 應用層：在共享能力之上，提供精簡的 use-case orchestration

高優先級發現
------------

1. Composition root 目前同時承擔平台選擇、lazy import、logging 設定、config 路徑策略、backend wiring 與 app 物件建構。
檔案：
- src/apps/nvda_remote/main.py
- src/apps/key_echo/main.py

影響：
- 違反 SRP。這些模組同時負責 bootstrap、平台偵測、基礎設施 wiring 與 runtime policy。
- 違反 OCP。只要新增平台或輸出 backend，就得直接修改這些 entry 模組。
- 不利未來重用。第三個 app 很可能又會複製更多這類 wiring。

建議：
- 抽出共享的 runtime builder 層，例如：
  - src/bootstrap/platform.py
  - src/bootstrap/output_registry.py
  - src/bootstrap/runtime_factory.py
- app main 模組應維持精簡 entrypoint：
  - 設定 process
  - 向 runtime factory 取得 AppRuntime
  - 啟動 UI / app loop

2. App service 混合了 use-case orchestration、裝置生命週期控制與 transport event handling。
檔案：
- src/apps/nvda_remote/service.py
- src/apps/key_echo/service.py

影響：
- 違反 SRP。NvdaRemoteAppService 同時處理 connection flow、control mode state、keyboard forwarding、hotkey toggle、message routing、clipboard、speech backend UI concern，以及 error / status dispatch。
- 違反 ISP。UI 實際上依賴的是一個很大的 ad hoc controller surface，而不是聚焦的介面。
- 未來 app 不是複製這種模式，就是被迫承接過多行為。

建議：
- 將 app service 拆成更聚焦的 use case：
  - ConnectionController / RemoteSessionController
  - ControlModeController
  - InputForwardingUseCase
  - SpeechSettingsUseCase
  - ClipboardSyncUseCase
- UI 應依賴針對該畫面設計的 presenter 或 controller 介面，而不是整個 service 物件。

3. Output abstraction 目前仍以 speech 為中心，還不是真正的多模態輸出架構。
檔案：
- src/application/output_service.py
- src/application/output_capabilities.py
- src/application/services.py
- src/adapters/outputs/interfaces.py

影響：
- 共享輸出層目前實際上比較像「speech backend 管理，加上一些可選的 tone / braille 欄位」。
- Tone、wave、braille 雖然有 protocol，但還沒有對應的 application service 模型。
- 當上層 app 需要以下協調輸出策略時，這個結構很難擴充：
  - speak + tone 同時輸出
  - 中斷 speech，但不中斷 sound effect
  - tone 有自己獨立的 queue
  - 依 capability availability 決定輸出路由

建議：
- 引入以 capability 為核心的 output facade，例如：
  - OutputBus 或 OutputRouter
  - SpeechChannel
  - ToneChannel
  - WaveChannel
  - BrailleChannel
- 針對每種 capability 定義獨立 service protocol，而不是只圍繞 speech 設計一個大介面。
- 將 scheduling policy 移到 per-channel 或協調式輸出 orchestration，而不是只埋在 speech implementation 裡。

4. Protocol 與 app event flow 目前偏向 dictionary-based，型別不夠強。
檔案：
- src/apps/nvda_remote/service.py
- src/interop/protocol/routing/message_router.py
- src/interop/protocol/session/remote_session.py
- src/application/state.py

影響：
- 在實務上違反 ISP 與 DIP，因為很多層之間透過鬆散的 dict payload 和 stringly typed state 溝通。
- 當未來要加入更多 event type、裝置事件或輸出事件時，演進成本會提高。
- 也會加深 UI 對內部 status payload 結構的耦合。

建議：
- 用 typed domain event 取代 status dict，但 remote 專屬 event 不應放進共享基礎層：
  - 共享 capability / runtime event：
    - InputCaptureStarted
    - InputCaptureStopped
    - ErrorRaised
    - SpeechBackendChanged
    - ClipboardAvailabilityChanged
  - remote domain event：
    - RemoteConnectionStateChanged
    - RemoteControlStateChanged
    - RemoteSessionJoined
    - RemoteVersionMismatch
- 用更嚴格的 state model 和 transition，取代 RuntimeState 的字串聯集。
- MessageRouter 和 RemoteSession 應輸出 typed event，而不是 generic dict payload。

依 SOLID 原則拆解
-----------------

S：Single Responsibility Principle
- 做得不錯的地方：
  - src/interop/protocol/serializer.py 職責集中。
  - src/interop/key/key_event.py 職責集中。
- 需要改善的地方：
  - src/apps/nvda_remote/main.py 變更原因過多。
  - src/apps/nvda_remote/service.py 變更原因過多。
  - src/application/output_service.py 把 speech control proxying 和 scheduler shutdown lifecycle 混在一起。

重構目標：
- 一個模組處理 process / bootstrap
- 一個模組處理 platform adapter resolution
- 每個 use case 一個模組
- 每個 output capability orchestration concern 一個模組

O：Open / Closed Principle
- 目前平台 / backend 選擇大多依賴 sys.platform 的 if/else，加上 hidden import wiring。
- 未來新增 Linux、另一種 speech backend，或另一種 input source，都需要修改中央檔案。

重構目標：
- 透過 factory 註冊 adapter / backend：
  - InputCaptureFactory
  - HotkeyCaptureFactory
  - ClipboardFactory
  - SpeechBackendRegistry
  - OutputCapabilityRegistry
- app code 透過介面要求能力，而不是走平台分支

L：Liskov Substitution Principle
- 目前 protocol 大多偏小，替換性還算合理。
- 風險點在 speech implementation 的行為保證其實不同：
  - pyttsx3 高度依賴 OutputScheduler
  - NVDA controller 的 pause / voice semantics 不同
  - NullSpeechOutput 相對於其他地方期待的完整 protocol，實作仍不完整

重構目標：
- 定義明確的 capability contract 與 optional feature：
  - SupportsVoices
  - SupportsPause
  - SupportsProsody
- 不要用一個胖介面逼每個 speech adapter 假裝支援所有功能

I：Interface Segregation Principle
- 這是目前最大的問題。
- SpeechOutput 和 SpeechOutputService 都是偏 UI 導向的大介面。
- App service 也暴露了太大的 controller surface，所有畫面都整包依賴。

重構目標：
- 依 use case 拆分介面：
  - SpeechPlayback
  - SpeechVoiceConfiguration
  - SpeechProsodyConfiguration
  - ClipboardRead
  - ClipboardWrite
  - InputCaptureControl
  - HotkeyCaptureControl
- 讓每個 UI 畫面只依賴自己真正需要的那一小部分

D：Dependency Inversion Principle
- 目前已有一些不錯的 protocol 使用方式：
  - Transport
  - InputCapture
  - HotkeyCapture
  - ClipboardService
- 但 composition root 和 service 仍然知道太多具體平台細節。
- importlib-based lazy loading 更像是把依賴問題藏起來，而不是明確建模。

重構目標：
- 將平台偵測移到 provider 物件之後：
  - PlatformInputProvider
  - PlatformOutputProvider
  - PlatformPermissionProvider
- 高層 app service 應依賴這些 abstraction，而不是直接依賴 runtime import logic

架構建議
--------

建議的目標分層：

1. interop/
- protocol framing、wire model、serializer、transport contract

2. domain/
- key event、speech / tone / wave / braille command
- 共享 capability / runtime event
- 涉及 remote 功能時，再放 remote domain state model 與 event

3. application/
- 只放 use case
- 不出現平台分支
- 不出現 importlib lazy loading
- 不出現 wx 型別

4. infrastructure/
- windows/、macos/、未來的 linux/
- input hook、clipboard、speech driver、tone / wave / braille driver
- provider / factory implementation

5. bootstrap/
- runtime composition
- configuration loading
- logging setup
- platform / provider registration

6. ui/
- wx view 與 presenter / controller
- 只依賴 application 介面

具體重構步驟
------------

Phase 1：穩定邊界
- 將 dict 型別的 status / event 抽成 typed class，但要明確拆開共享 capability event 與 remote 專屬 event。
- 將 logging / config path logic 從 app main 模組移到 bootstrap helper。
- 將 platform adapter resolution 從 app main 模組移到 provider / factory。

Phase 2：拆分過大的 service
- 將 NvdaRemoteAppService 拆成聚焦的 use-case class。
- 如果 UI 需要方便呼叫，可以保留一層很薄的 facade。
- 不要再讓單一 class 同時管理 transport / input / hotkey lifecycle。

Phase 3：重設 output 架構
- 將 speech、tone、wave、braille 建成一等公民的 output channel。
- 用 output service registry 或 output bus 取代 OutputCapabilities dataclass。
- 為每種 capability 建立自己的 contract，以及 scheduling / interruption policy。

Phase 4：統一 input 架構
- 定義共享的 input event pipeline：
  - raw capture
  - normalized input event
  - command mapping / hotkey policy
  - app use-case handling
- 這樣 app service 就不用自己持有低階 key semantics。

Phase 5：建立 app-facing SDK surface
- 對未來 app 暴露可重用的 application 介面，讓它們不需要知道平台細節：
  - InputService
  - OutputServiceRegistry
  - 若有 remote 功能需求，再加 ConnectionUseCases
  - Event subscription API

建議的檔案層級調整
------------------

- src/apps/nvda_remote/main.py
  拆成 bootstrap / process entrypoint，以及 nvda_remote runtime assembly。

- src/apps/key_echo/main.py
  重用相同的 bootstrap / runtime assembly pattern，而不是維護另一套自訂 composition root。

- src/apps/nvda_remote/service.py
  拆出 connection、control、clipboard、speech settings、hotkey toggle 等責任。

- src/apps/key_echo/service.py
  改成建立在共享 input / speech application service 之上的薄 facade。

- src/application/output_service.py
  不要再把所有 output concern 建模成「speech service 加上一層 scheduler shutdown wrapper」。

- src/application/services.py
  要嘛把 OutputManager 縮成特定的 remote-output use case，要嘛把 clipboard / speech handling 拆成各自獨立的 use case。

- src/adapters/outputs/interfaces.py
  把過大的 speech contract 拆成較小、可選的 capability contract。

- src/application/state.py
  用更強型別的 state transition 或 state object，取代寬鬆的 string union。

若不重構的殘餘風險
------------------
- 每新增一個 app entrypoint，都會再複製 composition 與平台邏輯。
- Tone / wave / braille 支援會一直是次等公民，很難優雅協調。
- UI 與 application logic 會持續透過 ad hoc controller method 與 dict event 緊耦合。
- 平台擴充只會讓 conditional complexity 持續增加，而不是新增可插拔 provider。

建議優先做的第一個里程碑
------------------------
如果只能先做一個重構，建議優先做這件事：

抽出共享的 bootstrap / provider layer，並拆分 NvdaRemoteAppService。

這件事槓桿最高，因為它同時改善 SRP、OCP、ISP 與 DIP，也能替後續的多模態輸入 / 輸出架構建立必要的接縫。
