# 架構重構檢視 v2

脈絡
----
這份檢視延續自 `docs/refactor/refactor1.md`，以及後續完成的 output package 重整。

和第一次檢視相比，程式碼目前已有幾個明顯改善：
- `application.output` 現在已經是一個真正的 package，而不是散落在
  `application/` 下的多個 output 相關模組。
- Speech backend 選擇已收斂在 `application.output.speech` 之下。
- Tone 已被表達成一種 output capability，而不是藏在 app 專屬程式碼裡。
- `apps/*/use_cases/` 已開始承接部分 app 邏輯，尤其是 key echo 和
  NVDA Remote 的 control / input forwarding。
- output 概念搬進 output package 後，runtime 欄位命名也比較不冗。

目前剩下的問題，已經比較不是檔案擺放位置，而是整體架構流程：runtime
composition 仍集中在 app entrypoint，app service 仍混合多種責任，status /
output / event flow 也仍偏向 ad hoc。

主要架構壓力點
--------------

1. Runtime composition 仍在 app entrypoint 間重複。

檔案：
- `src/apps/nvda_remote/main.py`
- `src/apps/key_echo/main.py`
- `src/apps/access8graph/main.py`
- `src/bootstrap/platform.py`

現況：
- 每個 app entrypoint 都在組裝 capture、hotkey capture、scheduler、
  speech、speaker、capabilities、app service、keyboard service 與 UI app。
- `bootstrap/platform.py` 同時包含平台偵測、lazy import、null fallback、
  clipboard factory、tone factory 與 speech backend 選擇。
- 目前的 composition pattern 已比以前一致，但仍有不少重複。

風險：
- 新增一個 app 時，很可能再複製一大段 runtime wiring。
- 新增平台或 backend 時，仍然得修改中央 factory 邏輯。
- app entrypoint 若要測試，仍需依賴大量 monkeypatch。

建議方向：
- 引入共享的 runtime composition 層，並保留 app 專屬 hook：
  - `bootstrap/providers.py`：平台 capability provider
  - `bootstrap/output.py`：speech / tone capability 組裝
  - `bootstrap/app_runtime.py`：共用 app runtime wiring
- 讓 app `main.py` 聚焦在：
  - 選擇 app 專屬 service class
  - 選擇預設 hotkey usage
  - 建立 UI shell
  - 啟動 app loop

遷移順序：
- 先從 `bootstrap/platform.py` 抽出 `PlatformProvider` 物件。
- 抽出共用的 `build_output_capabilities()` helper。
- 把各 app `main.py` 中共通的 keyboard / hotkey / speech / speaker wiring
  移出。
- 在測試全面改用 provider API 前，暫時保留既有 factory function 當相容包裝。

2. App service 仍然是 facade / controller 的混合體。

檔案：
- `src/apps/nvda_remote/service.py`
- `src/apps/key_echo/service.py`
- `src/apps/access8graph/service.py`
- `src/apps/shared/speech_settings_controller.py`
- `src/apps/shared/mode_manager.py`

現況：
- `NvdaRemoteAppService` 同時持有 connection / session 行為、mode switching、
  keyboard forwarding、clipboard push、speech settings、tone routing、status
  dispatch、input capture lifecycle、hotkey 行為，以及 transport message
  handling。
- `KeyEchoAppService` 和 `Access8GraphAppService` 雖然比較小，但仍同時承擔
  UI-facing controller method 與較低階的 input / hotkey lifecycle。
- `ModeManager` 是很有價值的共享抽象，但 app service 本身仍承接太多周邊協調。

風險：
- UI controller 依賴的是很大的 service 物件，而不是聚焦的介面。
- 每增加一個 mode 或 app feature，單一 service class 的 surface area 都會擴大。
- 因為責任沒有被清楚隔離，integration test 會變成唯一實際可用的驗證方式。

建議方向：
- 將 app service 視為建立在聚焦 use case 之上的薄 facade。
- NVDA Remote 至少可拆成以下幾個單元：
  - `RemoteConnectionUseCase`
  - `RemoteControlUseCase`
  - `RemoteMessageHandlingUseCase`
  - `ClipboardSyncUseCase`
  - `RemoteStatusPresenter` 或 `StatusEventSink`
- 讓 UI-facing service 將工作委派給這些單元，而不是自己持有全部邏輯。

遷移順序：
- 優先從 `NvdaRemoteAppService` 開始，它的責任密度最高。
- 先抽出 transport / session connection 邏輯，因為它和 key forwarding
  的耦合相對較低。
- 在拆更多 UI-facing method 之前，先把 status dispatch 轉成 typed event。
- 在 UI 仍依賴舊 surface 時，保留一層小型 `NvdaRemoteAppService` facade。

3. Status 與 event flow 應轉為 typed。

檔案：
- `src/apps/nvda_remote/service.py`
- `src/apps/access8graph/service.py`
- `src/apps/key_echo/service.py`
- `src/interop/protocol/routing/message_router.py`
- `src/interop/protocol/session/remote_session.py`
- `src/application/state.py`

現況：
- App service 目前用字典發布 status，例如
  `{"kind": "error", "message": ...}` 與
  `{"kind": "speech_backend", "backend_id": ...}`。
- Remote session 與 router 的狀態也透過鬆散的 payload 傳遞。
- UI 程式碼實際上會隱性依賴這些字典的 shape。

風險：
- Event contract 無法從型別直接發現。
- 只要改一個 status key 名稱，或新增一種 event shape，就可能悄悄破壞 UI。
- 共享 application event 與 app-domain event 現在混在一起。

建議方向：
- 引入 typed event dataclass。
- 把共享 runtime event 和 app-domain event 分開。

候選的共享 event：
- `ErrorRaised`
- `InputCaptureChanged`
- `HotkeyCaptureChanged`
- `SpeechBackendChanged`
- `ClipboardAvailabilityChanged`

候選的 NVDA Remote event：
- `RemoteConnectionChanged`
- `RemoteControlChanged`
- `RemoteSessionJoined`
- `RemoteProtocolWarning`
- `RemoteTransportDisconnected`

遷移順序：
- 在 `application/events.py` 或 `apps/shared/events.py` 下加入 event dataclass。
- 先讓一個 app service 在內部改發 typed event，同時在 UI 邊界保留既有 dict
  adapter。
- 再讓 UI controller 改成直接消費 typed event。
- 等所有 app UI 都遷移後，再移除 dict adapter。

4. Output 結構已較清楚，但仍未成為完整的多模態輸出架構。

檔案：
- `src/application/output/capabilities.py`
- `src/application/output/service.py`
- `src/application/output/scheduler.py`
- `src/application/output/manager.py`
- `src/application/output/speech/service.py`
- `src/adapters/outputs/interfaces.py`
- `src/apps/access8graph/output.py`

現況：
- `Capabilities` 目前暴露 speech、tone 與 braille slot。
- `QueuedService` 透過共用 scheduler 協調 speech queueing。
- Speech 已有 backend 管理與設定能力；tone 和 braille 則仍是較簡單的可選 adapter capability。
- `Manager` 仍偏向 remote-message 導向：speech、cancel、pause、tone 與
  clipboard routing 還是放在一起。

風險：
- 只要 tone、wave、braille 的行為變多，就會繼續被當成次等公民。
- Scheduling / interruption policy 仍過度偏向 speech。
- 若 app 需要協調輸出，例如 speech + tone 或 speech + braille，就會被迫自己做客製 orchestration。

建議方向：
- 逐步把 `Capabilities` 演進成明確的 output channel：
  - `SpeechChannel`
  - `ToneChannel`
  - `BrailleChannel`
  - `WaveChannel`
- 在 channel 行為還不夠多之前，保留 `Capabilities` 作為 app-facing bundle。
- 如果 `Manager` 仍主要服務 protocol message，應將它拆成 remote output handler。

遷移順序：
- 先在 `application.output` 裡定義較小的 protocol：
  - speech playback
  - speech settings
  - tone playback
  - braille display
- 把 remote protocol output routing 從過於通用的 `Manager` 命名中移出。
- 只有在 app 真正需要 tone 專屬 queueing 或 cancellation policy 時，再加入
  tone channel orchestration。
- 至少等兩種 output channel 需要共享協調時，再引入完整的 `OutputBus`。

5. Input 架構已有部分可重用性，但還不是共享的 command pipeline。

檔案：
- `src/application/input/`
- `src/application/keyboard.py`
- `src/apps/shared/mode_manager.py`
- `src/apps/key_echo/use_cases/echo_input.py`
- `src/apps/nvda_remote/use_cases/input_forwarding.py`
- `src/apps/access8graph/input.py`

現況：
- 低階 capture 已藏在 adapter protocol 之後。
- `InputActivationUseCase` 和 `ModeManager` 提供了有價值的共享行為。
- 但各 app 仍分別持有自己的 key translation 與 command decision 邏輯。

風險：
- 新 app 很容易再次重複 keyboard pipeline 邏輯。
- Hotkey enter / exit 行為可能逐漸在不同 app 間漂移。
- Accessibility graph navigation、key echo 與 remote forwarding 現在都各自用不同方式編碼 command mapping。

建議方向：
- 建立共享的 input command pipeline：
  - captured event
  - normalized key event
  - app mode selection
  - command translation
  - app use-case execution
  - system pass-through decision
- 讓 app-specific translator 保留彈性，但統一其 contract。

遷移順序：
- 先引入共享的 `CommandTranslator` protocol。
- 先把 key echo 與 access8graph translator 對齊到同一個 protocol。
- 把 system pass-through decision 移到單一 policy layer。
- 在 remote key payload 尚未和 local key event 完整分離前，保留 remote
  forwarding 的特殊處理。

6. Repository hygiene 不應讓產生檔主導架構觀察。

檔案與目錄：
- `src/**/*.pyc`
- `src/**/__pycache__/`
- `*.egg-info/` 這類 install metadata

現況：
- Repo 已經移除被追蹤的 `egg-info` 檔案。
- 但本地 generated file 仍會在廣義掃描時出現在工作樹中。

風險：
- 產生檔會讓架構檢視變得很吵。
- 過期的 generated metadata 可能仍指向已刪除模組，干擾未來重構判斷。

建議方向：
- 將 Python cache、build output 與 install metadata 排除在 git 追蹤之外。
- 若尚未設定，補上 `*.egg-info/` 的 ignore 規則。
- 架構盤點時，優先使用 `git ls-files` 這類 source-level 清單。

目標架構
--------

建議的長期分層如下：

1. `interop/`
- 承接 protocol message、serialization、transport contract、session 機制。
- 不出現 wx、不出現平台 import、不出現 app UI 行為。

2. `application/`
- 承接共享 input、output、runtime event、scheduling 與 capability contract。
- 不出現平台分支。
- 不出現 app 專屬的 remote workflow。

3. `apps/shared/`
- 可重用的 app-facing controller 與 mode orchestration。
- 提供 UI integration 所需的 shared presenter 或 typed event adapter。

4. `apps/<app>/use_cases/`
- 放 app 專屬的 business behavior。
- remote control、key echo、graph navigation 的 use case 都應留在這裡。

5. `apps/<app>/service.py`
- 作為 UI 與 runtime wiring 之間的薄 facade。
- 將工作委派給 use case，並暴露小而聚焦的 screen-specific API。

6. `adapters/`
- 放平台與 driver implementation。
- 包含 Windows、macOS、未來 Linux，以及 speech engine、tone / braille /
  wave driver。

7. `bootstrap/`
- 負責 provider selection、runtime composition、config path、logging setup。
- 只有這一層應知道如何把 adapters 組成 app。

8. `ui/`
- 放 wx view、frame 與 UI controller。
- 依賴 app-facing interface 與 typed event。

建議路線圖
----------

Phase 1：抽出 runtime provider
- 從 `bootstrap/platform.py` 抽出平台 provider 物件。
- 從 app `main.py` 抽出共通 runtime wiring。
- 保持行為不變，並沿用既有測試保護。

Phase 2：遷移到 typed event
- 為共享 runtime event 與 app-domain event 建立 dataclass。
- 讓 app 逐步改成內部發送 typed event。
- 在過渡期保留對既有 UI dict payload 的 adapter。

Phase 3：拆分 `NvdaRemoteAppService`
- 抽出 connection / session 行為。
- 抽出 remote message handling。
- 抽出 clipboard sync。
- 保留一層薄的 UI-facing facade。

Phase 4：演進 output channel
- 依 capability 拆分 output protocol。
- 如果 `Manager` 仍偏向 protocol message 導向，就縮窄或改名。
- 只有在真的出現協調策略時，才加入 channel 物件。

Phase 5：建立共享 input command pipeline
- 標準化 command translator contract。
- 將共用的 pass-through 與 mode decision 行為收斂到 shared policy。
- 保留 app-specific command mapping 的隔離。

Phase 6：縮小 UI 依賴面
- 讓每個 frame 依賴一個小而聚焦的 controller protocol。
- 避免把整個 app service 傳進 UI class，卻只用其中一小部分。
- 把大量依賴 monkeypatch 的測試，逐步改成 controller-level test。

建議的下一個里程碑
------------------

如果下一個長期重構只能先做一件事，建議先做 runtime provider extraction。

原因：
- 它能降低所有 app entrypoint 的重複 wiring。
- 它能建立平台與 output provider registration 的自然落點。
- 它能讓後續 app-service 拆分拿到更乾淨的依賴。
- 相較於先拆 `NvdaRemoteAppService`，它的行為風險較低。

第二個里程碑應該是 typed event。若沒有 typed event contract，service
即使拆開，也只是把鬆散的 dict 在更多地方傳遞，無法真正改善 UI 與
application 邊界。
