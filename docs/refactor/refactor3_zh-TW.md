# 架構重構檢視 v3

背景
----
這份檢視是拿 `docs/refactor/refactor2.md` 和目前的程式碼庫狀態做比較。

`refactor2.md` 在當時正確抓到了主要的架構壓力點，但其中一部分建議的工作其實已經落地：

- 共用的 runtime 組裝層現在已經存在於：
  - `src/bootstrap/platform.py`
  - `src/bootstrap/output.py`
  - `src/bootstrap/app_runtime.py`
- 共用的 typed application event 現在已經存在於：
  - `src/application/events.py`
- 各 app 專屬的 typed event 現在已經存在於：
  - `src/apps/key_echo/events.py`
  - `src/apps/access8graph/events.py`
  - `src/apps/nvda_remote/events.py`
- Input / mode activation 已經透過以下元件變得更一致：
  - `src/application/input/`
  - `src/apps/shared/mode_manager.py`
- Key echo 與 NVDA Remote 的部分邏輯也已經移進聚焦過的 use case。

因此，下一波重構不應再從頭重做 bootstrap 抽取，也不該重新爭論 typed event
這件事本身。現在剩下的工作，比較像是把那些只做了一半的邊界正式補完。

相較 v2 的變化
--------------

1. Runtime composition 已經不是風險最高的問題。

`refactor2.md` 建議抽出共用 runtime builder，這件事現在大致上已經完成。各 app
的 entrypoint 雖然還是保留一些 app-specific wiring，但原本大量重複的平台 /
output 組裝邏輯，現在已經集中管理。

目前判斷：
- 這一塊還是有少量重複，但已經不是最主要的架構瓶頸。
- 現在剩下的重複，比較集中在 speech setting 持久化與一些 app-specific 啟動政策。

2. Typed event 已經存在，但 protocol layer 仍然是 dict-first。

目前程式碼庫已經有 app 與 shared runtime 的 typed event，但 NVDA Remote
仍然依賴一條過渡性的 dict-to-dataclass 橋接：

- `RemoteSession` 會發出 dict status payload。
- `MessageRouter` 會發出 dict status payload。
- `NvdaRemoteAppService` 再透過 `StatusEvent.from_payload()` 做轉換。

目前判斷：
- Event model 目前只遷移了一半。
- 外層 app 邊界已經 typed 化，但 protocol / session / router 這一層還沒有。

3. App service 的拆分程度仍然不平均。

目前已經有一些進展：
- `key_echo` 已經相對接近原本想要的 facade / use-case 形狀。
- NVDA Remote 雖然已經抽出 control / input-forwarding use case，但 app service
  本體仍然背了太多協調邏輯。
- Access8Graph 目前仍然比其他 app 更偏向 service-centric。

目前判斷：
- 下一波重構應該聚焦在補完 service 邊界，而不是再搬一次檔案位置。

更新後的架構壓力點
------------------

1. 把 protocol 邊界上的 typed event 補完。

檔案：
- `src/interop/protocol/session/remote_session.py`
- `src/interop/protocol/routing/message_router.py`
- `src/apps/nvda_remote/service.py`
- `src/application/events.py`
- `src/apps/nvda_remote/events.py`

現況：
- `RemoteSession` 會發出 connection 與 remote message 等 dict payload status。
- `MessageRouter` 會針對未知訊息與無效 payload 發出 dict payload status。
- `NvdaRemoteAppService` 目前仍然持有一層從 transport / router dict payload
  轉成 UI-facing typed event 的翻譯邏輯。
- `StatusEvent` 目前雖然定位為過渡 adapter，但實際上仍在正式架構路徑中，
  不只是相容性支援而已。

為什麼這件事現在是最高優先：
- 它卡住了 NVDA Remote 下一階段的 service 拆分。
- 它讓 protocol contract 仍然是隱性、偏 stringly typed。
- 它迫使 `NvdaRemoteAppService` 繼續承擔 event translation 這種本來應該更靠近
  protocol layer 的責任。

建議方向：
- 改成引入 protocol-facing typed event，而不是繼續傳 dict payload。
- 讓 `RemoteSession` 改成發出像這樣的 event：
  - `RemoteSessionConnected`
  - `RemoteSessionDisconnected`
  - `RemoteSessionVersionMismatch`
  - `RemotePeerMessageReceived`
- 讓 `MessageRouter` 改成發出 typed 的 protocol / runtime error，例如：
  - `RemoteProtocolMessageIgnored`
  - `RemoteProtocolMessageInvalid`
- 將 `StatusEvent` 限縮為測試 / 向後相容用途，之後再從正式流程中移除。

遷移順序：
- 先新增 protocol event dataclass。
- 再更新 `RemoteSession` 與 `MessageRouter`，讓它們內部直接發出 typed event。
- 接著讓 `NvdaRemoteAppService` 直接消費這些 event。
- 再把測試從 dict comparison 遷移出去。
- 等所有 caller 都遷移完後，再把 `StatusEvent` 從 production wiring 移除。

2. 把 NVDA Remote 的協調邏輯拆成 connection / protocol / presentation 單元。

檔案：
- `src/apps/nvda_remote/service.py`
- `src/apps/nvda_remote/use_cases/control_mode.py`
- `src/apps/nvda_remote/use_cases/input_forwarding.py`
- `src/interop/protocol/session/remote_session.py`
- `src/interop/protocol/routing/message_router.py`

現況：
- `NvdaRemoteAppService` 目前仍然自己負責：
  - transport binding
  - session lifecycle
  - router lifecycle
  - connection state transition
  - control start / stop orchestration
  - clipboard push
  - tone handling
  - remote status translation
  - capture / hotkey start-stop policy
- 目前已抽出的 use case 的確有幫助，但主要 service 仍然是整體架構的重心。

為什麼這是第二優先：
- 它目前仍是整個 repo 裡責任密度最高的 class。
- 剩下的複雜度已經不再只是 UI，而是 orchestration 與 protocol glue。
- 先完成上面的 protocol event 遷移，這一段拆分會更自然也更乾淨。

建議方向：
- 保留 `NvdaRemoteAppService` 當成 UI-facing facade。
- 把協調邏輯移到更聚焦的單元，例如：
  - `RemoteConnectionUseCase`
  - `RemoteProtocolEventHandler`
  - `RemoteClipboardUseCase`
  - `RemoteCapturePolicy`
- Key forwarding 與 control mode 若目前切分已經足夠，就先維持現狀。

遷移順序：
- 先抽出 connection / disconnection 與 connection-state handling。
- 再把 `_handle_transport_message()`、`_on_status()`、
  `_handle_connection_status()` 與 `_event_from_status()` 裡的 protocol event
  handling 抽出去。
- Clipboard push / tone routing 若在大拆之後仍不合適，再進一步拆開。
- 對外提供給 UI 的 controller API 先保持穩定。

3. 把 app entrypoint 中共用的 speech runtime settings policy 抽出來。

檔案：
- `src/apps/nvda_remote/main.py`
- `src/apps/key_echo/main.py`
- `src/apps/access8graph/main.py`
- `src/application/config.py`
- `src/apps/shared/speech_settings_controller.py`

現況：
- 三個 app entrypoint 都重複了幾乎相同的邏輯，用來處理：
  - 載入 selected engine
  - 套用已儲存的 voice / rate / pitch / volume
  - 持久化 engine / voice / numeric setting 的變更
- 這份重複現在特別顯眼，因為更底層的 runtime wiring 已經被集中化了。

為什麼這件事現在值得做：
- 這是跨 app 啟動流程裡少數仍明顯重複的區塊。
- 它把 persistence policy 混進本來應該主要只負責組裝 runtime part 的 entrypoint。
- 也讓 app runtime assembly 看起來比實際上更分歧。

建議方向：
- 引入共用 helper 或 coordinator，例如：
  - `SpeechRuntimeSettings`
  - `SpeechSettingsPersistence`
  - `bind_speech_settings_to_config_store(...)`
- 讓 app `main.py` 只需要宣告：
  - 預設 engine policy 是什麼
  - fallback 是否需要寫回持久化設定
  - 要建立哪個 UI app / controller

遷移順序：
- 先抽出重複的 `_apply_saved_speech_settings()` 邏輯。
- 再把 `SpeechSettingsController` 用到的 callback 綁定抽出去。
- 每個 app 的 default engine selection 若還有差異，可暫時留在 entrypoint。

4. 把 Access8Graph 拉到和其他 app 一樣的 service / use-case 水位。

檔案：
- `src/apps/access8graph/service.py`
- `src/apps/access8graph/input.py`
- `src/apps/access8graph/flow.py`
- `src/apps/access8graph/output.py`
- `src/apps/access8graph/events.py`

現況：
- `Access8GraphAppService` 目前仍直接持有：
  - graph file selection 驗證
  - flow 建立 / 銷毀
  - graph navigation lifecycle
  - error speech side effect
  - hotkey 啟動時的錯誤回報 policy
- `Access8GraphNavigationMode` 會直接呼叫 service 的 private method，例如
  `_start_flow()` 與 `_stop_flow()`。
- `Access8GraphKeyTranslator()` 也是在 mode handling 內直接 inline 建立。

為什麼這件事要排在 NVDA Remote 後面：
- 它沒有 transport / session layer，所以風險低於 NVDA Remote。
- 它的問題大多是局部性的，等 event / protocol model 更清楚後再處理會更順。

建議方向：
- 保留 `Access8GraphAppService` 作為薄 facade。
- 抽出更聚焦的單元，例如：
  - `GraphSelectionUseCase`
  - `GraphNavigationUseCase`
  - `GraphFlowFactory`
  - `Access8GraphCommandTranslator` protocol 或穩定的 translator 邊界
- 拿掉 mode 直接碰 private service method 的耦合。

遷移順序：
- 先抽出 flow 建立 / 銷毀。
- 再抽出 navigation lifecycle 與 hotkey 啟動 policy。
- 最後再決定 translator 標準化是否應該跨 app 共用，或維持 local 即可。

5. 釐清 `application.output.Manager` 到底還是不是一個有效抽象。

檔案：
- `src/application/output/manager.py`
- `src/interop/protocol/routing/message_router.py`
- 相關測試位於 `tests/unit/test_output_manager.py` 與
  `tests/unit/test_message_router.py`

現況：
- `Manager` 仍然存在，也有測試，但目前實際 runtime 路徑大多已改用
  `Capabilities`、`QueuedService` 與直接 router callback。
- 這個 class 名稱很泛，但責任其實偏窄，也有一部分已經帶有 legacy 性質。

為什麼這件事優先度較低：
- 它目前沒有直接卡住 app / service refactor。
- 目前更大的風險是概念混淆，而不是立即性的架構傷害。

建議方向：
- 在兩條路之中擇一：
  - 把它保留成小型的相容性工具，並重新命名或補文件說明
  - 等 protocol / output routing 穩定後，正式淘汰
- 這件事不要當作下一步的起手式。

從 v2 降低優先度的項目
----------------------

1. Bootstrap extraction 已經不再是下一步專案。

Provider / output / app runtime 這一層已經存在。剩下的只屬於增量清理，不再是基礎工程。

2. 現在不是推動完整通用 input command pipeline 的最佳時機。

目前程式碼庫其實已經有一些有價值的共用 input 元件：
- captured event abstraction
- app pipeline result helper
- activation policy
- mode management

Translator 與 command execution 仍然存在差異，但這件事目前不是最有槓桿的重構點。
先把 protocol event 與 app-service 邊界補完，之後再來統一 input，通常會更簡單。

3. 完整的 multimodal output bus 仍然可以再等等。

以目前 app 的需求來看，現在的 output 組織已經夠用。更大的問題仍然是 service
與 protocol 邊界，而不是缺少一個全面性的 output bus。

建議的下一個重構切片
--------------------

如果下一步只能選一條重構主線，建議順序是：

1. 把 app entrypoint 中共用的 speech runtime settings persistence 抽出來。
2. 完成 NVDA Remote 的 typed protocol event。
3. 以這些 typed event 為中心，拆分 NVDA Remote 的 app orchestration。

為什麼這個順序合理：
- 它會先移除幾個仍然存在的跨 app 啟動重複。
- 它是在補完 `refactor2` 已經啟動的工作，而不是另開新戰線。
- 它能接著移除目前最重要、尚未清掉的 dict-based 邊界。
- 它能在 protocol contract 更清楚之後，再縮小 repo 中最大的 service。
- 它能在不重新打開 bootstrap 問題的前提下，進一步簡化 app entrypoint。

下一階段的完成定義可以具體寫成：
- 共用的 speech settings 啟動 / 持久化邏輯，不再複製在三個 `main.py` 裡。
- `RemoteSession` 與 `MessageRouter` 在正式 production flow 中，不再發出
  dict status payload。
- `NvdaRemoteAppService` 變成包在更小 orchestration 單元外面的薄 facade。
- 現有 UI controller API 與行為保持穩定。

總結
----

相較於 `refactor2.md`，目前的架構已經走過「bootstrap extraction」階段，也部分走過了
「typed event」階段。因此下一步重構應該聚焦在補完，而不是為了重組而重組。

現階段價值最高的下一步，是先把 app entrypoint 裡重複的 speech settings
runtime policy 抽出來，接著把 NVDA Remote 的 typed protocol / event 邊界補完，
再利用這個邊界把剩下的協調邏輯從 `NvdaRemoteAppService` 裡拆出去。最後再把
Access8Graph 拉到和其他 app 一樣的 facade / use-case 水位。
