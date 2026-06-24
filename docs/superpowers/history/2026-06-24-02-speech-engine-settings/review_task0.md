# Task 0 Code Review Report

- 被審 commit:`56be8efa696da2b3c91ec2260122fa144c4524be` `feat: add speech engine settings`
- 對照規格:`docs/superpowers/specs/2026-06-24-speech-engine-settings-design.md`
- 對照計畫:`docs/superpowers/plans/2026-06-24-speech-engine-settings-implementation.md`
- 審閱者:專業程式開發審閱者(以 spec/plan 為基準逐項對照)
- 驗證命令:`python3 -m pytest tests/unit tests/integration -q` -> 581 passed

> 注意:計畫原訂以 10 個 task 各自產生獨立 commit(TDD 節奏),但本次開發壓成單一 commit。工作產物本身仍可審閱;以下以該 commit 內容為對象。

## 1. Strengths(符合規格/計畫的部分)

1. **核心模型與輔助函式**:`SpeechNumericSetting` dataclass 預設值(`default_percent=50`、`0..100`、`step=1`、`large_step=10`)與 `clamp_percent`/`percent_to_range`/`range_to_percent` 行為對應 spec「Common Helpers」與 plan Task 1,並有單元測試 `test_speech_numeric_setting_defaults_to_zero_to_one_hundred_percent`、`test_percent_helpers_clamp_and_map_ranges` 驗證。
2. **引擎命名與 id/label 固定值**:`SpeechEngineOption`/`SpeechEngineManager` 已實作;`NvdaController`/<`Nvda Controller`> 與 `Pyttsx3`/<`Pyttsx3`> 在 `bootstrap/platform.py:default_speech_engine_options` / `default_speech_engine_id` 中以平台條件正確組裝,符合 spec「Speech Engine IDs And Labels」。
3. **驅動端 owned settings**:PYTTSX3 與 NVDA Controller 都實作 `get_supported_numeric_settings()` 回傳 `rate`/`pitch`/`volume`,並以 normalized `0-100` 儲存、clamp 後再 setter,符合 spec「Driver-Owned Settings」與「Normalized Value Contract」。`Pyttsx3SpeechOutput._speak_text` 才將 percent 映射到 raw(rate 50-300、pitch 0-100、volume 0.0-1.0),`NvdaControllerSpeechOutput._speech_to_ssml` 將 baseline offset 透過 `(baseline+offset)/baseline*100` 轉 SSML prosody percent,與 plan Task 4 測試期望一致。
4. **NVDA Controller 在不可用時 `get_supported_numeric_settings() -> ()`**:符合「Unsupported numeric settings 直接反映於 UI」。
5. **Persistence**:`SpeechEngineConfigStore` 以 `speech_engine` + `speech_engines.<id>.{voice,rate,pitch,volume}` 為 schema,save/load 都做 `clamp_percent`,語音與設定只存 normalized percent,與 spec「Persistence」一致。`apps/nvda_remote/main.py:_apply_saved_speech_settings` 在 `voice in available_voice_ids` 才套用、僅對 `supported` 設定套用,符合 spec「ignore saved values for unsupported settings」/「ignore missing voice」。
6. **UI sliders + capability disabling**:`speech_controls.py` 改用 `wx.Slider(0..100)`、`_sync_numeric_slider` 對未支援 setting 設定 `SetValue(50)` + `Disable()`、`voice_choice` 在 `_voice_options` 為空時 `Disable()` + `SetSelection(-1)`,符合 spec「Panel Controls」與「Unsupported Numeric Settings」/「Voice Selection」。EVT_SLIDER 與 fake `wx.Slider` 同步加入測試。
7. **App-facing event**:`SpeechEngineChanged(engine_id)` 取代 `SpeechBackendChanged`,三個 app service(`nvda_remote`、`key_echo`、`access8graph`)的 `set_speech_engine` 都會 `_notify_status_listener(SpeechEngineChanged(...))`,符合 plan Task 6。
8. **Controller 回呼**:`SpeechSettingsController` 提供 `on_engine_changed`/`on_voice_changed`/`on_numeric_setting_changed`,且在成功 setter 之後才呼叫,符合 plan Task 8 Step 4 的「after successful changes」。`apps/nvda_remote/main.py` 將其接上 `config_store.save_*` 並在切換引擎時重跑 `_apply_saved_speech_settings`,符合 spec「Speech Engine Switch」流程。
9. **回歸/單元測試廣度**:drivers percent 映射、NVDA baseline+offset、config store 每引擎 clamp、UI slider/disabled/voice、bootstrap id/label、app service dispatch、controller pass-through + callbacks、main 重新載入設定均有覆蓋。

## 2. Important Issues(偏離 spec/plan,建議處理)

### I-1 引擎切換失敗時舊引擎已被 cancel,違反「keep current engine active」

`src/application/output/speech/backends.py:48-56` `SpeechEngineManager.set_engine`:

```python
self._current_output.cancel()
self._current_output = self._create_output(engine_id)
self._selected_engine_id = engine_id
```

`cancel()` 在 factory 之前呼叫。若 `_create_output`(=引擎 factory,例如 `Pyttsx3SpeechOutput.load_default`、`NvdaControllerSpeechOutput.load_default`)丟出例外,舊引擎已被 `cancel()` 但 `_selected_engine_id` 未更新,結果是「已死的舊引擎仍對外回報為 selected」。`UI._on_speech_engine_change` 雖 try/except 後再 `_sync_speech_engine_choice()`,但無法讓舊引擎恢復可運作。

spec「Error Handling」明文要求:**「If switching to a new speech engine fails, keep the current engine active and restore the previous UI selection.」** 目前未達成,且無測試覆蓋此情境。

建議:先 `new_output = self._create_output(engine_id)`(外包 try/except),成功後才 `self._current_output.cancel()` 並以新替舊;失敗則保留原 `current_output` 與 `selected_engine_id`,讓 UI `_sync_speech_engine_choice` 自動回到原選項。

### I-2 大量 backend 相容別名遺留,違反 plan Task 9 且 Non-Goal 不一致

plan Task 9 明確要求 `rg "SpeechBackend|speech_backend|get_speech_backend|set_speech_backend|selected_backend|backend_options|backend_id|SpeechBackendChanged"` 並以 `SpeechBackend -> SpeechEngine` 等取代。spec Non-Goals 雖僅禁止「`speech_backend` config key」相容,但 plan 與設計「Move terminology from `backend` to `speech engine`」一致。實作仍保留約 30 處別名 shim:

- `backends.py`:`SpeechBackendOption = SpeechEngineOption`、`SpeechBackendManager = SpeechEngineManager`、`selected_backend_id` property、`backend_choices()`、`set_backend()`。
- `application/output/speech/__init__.py`:仍匯出 `SpeechBackendManager`/`SpeechBackendOption`。
- `application/output/speech/service.py` 與 `application/output/service.py`:`SpeechService` 與公開 `SpeechServiceProtocol` 都保留 `get_backend_options()`/`get_selected_backend()`/`set_backend()`。
- `application/events.py`:`SpeechBackendChanged = SpeechEngineChanged`。
- `application/config.py`:`load_backend_id`/`save_backend_id`/`SpeechBackendConfigStore = SpeechEngineConfigStore`。
- `bootstrap/platform.py`:`PlatformProvider.default_speech_backend_options/_id` 與模組級 `default_speech_backend_options/_id` 別名,註解「Temporary aliases until all call sites are migrated」。
- `bootstrap/output.py`、`bootstrap/app_runtime.py`:建構子重複接受 `backend_options_factory`/`selected_backend_id`/`fallback_backend_id`/`on_backend_fallback` 並以 `or` 取代。
- 三個 app service:`get_speech_backend_options`/`get_selected_speech_backend`/`set_speech_backend`。
- UI `speech_controls.py`:`speech_backend_choice = speech_engine_choice`、`rate_ctrl = rate_slider`、`_on_speech_backend_change`、`_sync_speech_backend_choice`、`_get_speech_backend_options`、`_get_selected_speech_backend`、`_backend_id_for_selection`。
- `apps/nvda_remote/main.py`:匯入 `getattr(config_store, "save_backend_id", ...)` 等 fallback。

finish_task0.md 已自承「Transitional backend compatibility aliases remain in place」。此為已知技術債。**問題不在別名本身**,而在別名被加進了**新建立**的程式碼(本 PR 自己引入的程式碼也加了別名,變成自我引用),且連帶產生下列 I-3 的死分支防禦程式。

建議:若其他模組確實還在用舊 API,在這些模組完成遷移後立即移除所有 shim;否則 spec/plan 未完成的「rename」就仍待收尾。請在 follow-up task 追蹤。

### I-3 `hasattr`/`inspect.signature` 死分支防禦程式

由於新 API 已永久存在,下列檢查永遠走新分支,屬 dead code / 過度防禦:

- `src/bootstrap/app_runtime.py:38-45`:`hasattr(provider, "default_speech_engine_id")` / `default_speech_engine_options`(`PlatformProvider` 永遠有)。
- `src/apps/nvda_remote/main.py:50-57`:`hasattr(config_store, "load_engine_id")`(`SpeechEngineConfigStore` 永遠有)。
- `src/apps/nvda_remote/main.py:107-110`:`hasattr(parts.output.speech, "get_selected_engine")`(`SpeechService` 永遠有)。
- `src/apps/nvda_remote/main.py:113-120`:`save_engine_id`/`save_backend_id` 取值分支。
- `src/apps/nvda_remote/main.py:145-149`:`if "on_speech_backend_changed" in inspect.signature(NvdaRemoteAppService).parameters`(建構子已固定有 `on_speech_backend_changed` 參數)。
- `src/apps/shared/speech_settings_controller.py:17`:`self._on_engine_changed = on_engine_changed or on_backend_changed`(配合 plan 但別名層層疊加)。

這些分支讓呼叫流程難以追蹤,且會誤導未來讀者以為舊 API 還可能存在。建議在移除 I-2 別名時一併清掉。

### I-4 缺整合測試:spec「Integration Tests」三項均未落實

spec「Testing Strategy / Integration Tests」要求三項:

1. 啟動單一引擎、persist、重啟後確認同一引擎與 normalized 值還原。
2. 切換引擎後確認「每引擎」設定被套用而非全域。
3. 進入的 speech sequences 仍透過所選引擎路由未變。

`tests/integration/` 僅有 `test_access8graph_mrt_flow.py`、`test_relay_session.py`,皆未涵蓋 speech engine。finish_task0.md 報告 6 個整合測試通過,但係不相關案例。plan Task 10 僅以「run full suite」收尾,未在前述 task 安排整合測試。重要缺口。

建議:新增 `tests/integration/test_speech_engine_*.py` 至少覆蓋上述三項(可用 fake transport + fake config path + fake driver,在 `SpeechService`/`SpeechEngineConfigStore` 真實實例上操作)。

## 3. Minor Issues

- **M-1 `percent_to_range`/`range_to_percent` 型別與 spec 不符**:spec「Common Helpers」指定 `percent_to_range(percent: int, min_value: float, max_value: float) -> float` 與 `range_to_percent(raw: float, ..., ) -> int`;實作改用 `int`/回傳 `int`。目前驅動(pyttsx3、volume `/100.0` 與 nvda SSML 整數 percent)夠用,但對外 helper contract 偏離設計。建議依 spec 改回 `float` 或更新 spec。
- **M-2 `load_numeric_setting` 接受 `bool`**:Python 中 `isinstance(True, int)` 為真,config 中若誤存 `true` 會被當成 `1` 載入;非影響功能但語意不嚴謹。可加 `isinstance(value, int) and not isinstance(value, bool)`。
- **M-3 `apps/key_echo/main.py` 未更新術語**:仍 `selected_backend_id="Pyttsx3"`、`fallback_backend_id="Pyttsx3"`(plan File Structure 表未涵蓋此檔,但 Task 9 要求全域替換)。靠 `app_runtime.py` 的 `or` fallback 運作;請隨 I-2/I-3 一併遷移。
- **M-4 `_DEFAULT_ENGINE_OPTIONS` 寫死在 UI mixin**:當 `controller` 為 None 或 controller 不提供 `get_speech_engine_options` 時 Falling back 至 hardcode `(("NvdaController", "Nvda Controller"), ("Pyttsx3", "Pyttsx3"))`。實務上 controller 一定有,但此 fallback 與驅動模組重複知識;日後新增引擎須兩處維護。可改要求 controller 必傳或拋錯。
- **M-5 `NvdaControllerSpeechOutput._normalized_percent_to_ssml_percent` 將 `value<=0` 直接回 0**:對 volume 而言等同靜音;對 rate/pitch 則 SSML `rate="0%"` 與 `pitch="0%"` 語意由引擎決定。屬驅動策略可接受,但 spec 並未明示 `0` 對應 SSML `0%` vs NVDA 語意;建議在 docstring 註明。
- **M-6 單一 squashed commit 與計畫不符**:plan Task 1~9 各有 `git commit -m ...` 步驟;實作壓成單 commit。對審閱者不易逐任檢視演進,但內容已審;僅記錄為流程偏離。
- **M-7 `SpeechService.__init__` 同時接受 `engine_options` 與舊 `backend_options` 兩套關鍵字並以 `or` 取後者,`SpeechService.single_backend` 內仍用 `engine_id="default"`**:與其它 fake 使用者一致,但「default」為測試專屬 id;正式出廠不會經過 `single_backend`,可接受。

## 4. 結論與建議優先順序

整體功能性符合 spec 與 plan:normalized 0-100 slider、driver-owned mapping、per-engine persistence、capability-driven disabling、engine 術名/id/label 都已落地,且 581 個測試通過。**可以以現況先合入**,但建議於合入前或緊接其後的 follow-up PR 處理:

1. **(Important) I-1**:修正 `SpeechEngineManager.set_engine` 失敗時保留舊引擎,並補測試「切換失敗 → 舊引擎仍可用 + UI 回原選」。
2. **(Important) I-4**:補三項 spec integration tests。
3. **(Important) I-2 + I-3**:規劃 backend alias 清掃 task;一併移除新檔內的死分支 `hasattr`/`inspect` 防禦;更新 `apps/key_echo/main.py` 與 `bootstrap/*` 呼叫端語。
4. **(Minor) M-1~M-7** 排入清理。

無 Critical 阻擋項。