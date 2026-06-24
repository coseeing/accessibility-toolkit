# Task 1 Review Report — 修正審閱

- 被審範圍:`git status` 顯示之工作區變更(對 `56be8ef` 的未提交修正)
- 對照:`docs/superpowers/review_task0.md` 提出的 4 個 Important 與 7 個 Minor
- 審閱方式:`git diff` 逐項對照實作 + 規格與計畫 + 執行完整測試套件
- 驗證命令:`python3 -m pytest tests/unit tests/integration -q` → **587 passed**(review_task0 基線 581 → 增加 I-1/M-1/M-2/I-4 等新測試,移除 2 個純別名測試;全部通過、無 FAILED/error)

## 1. 逐項修正驗證

### I-1 引擎切換失敗保留舊引擎 — 已完成 ✅
`src/application/output/speech/backends.py:41-55` `set_engine` 改為:
```python
new_output = self._create_output(engine_id)   # 失敗時不破壞現狀
previous_output = self._current_output
previous_output.cancel()
self._current_output = new_output
self._selected_engine_id = engine_id
```
factory 丟例外 → `_current_output` 與 `_selected_engine_id` 皆未動,符合 spec「Error Handling」。
另附註解引用 spec 出處,可讀性佳。

覆蓋測試:
- `tests/unit/test_speech_backends.py::test_speech_engine_manager_keeps_current_engine_on_factory_failure` — 以 `FactoryError` 斷言 `current_output is previous_output`、`selected_engine_id` 未變、`events == []`(確認舊引擎未被 cancel)。
- `tests/integration/...::test_engine_switch_failure_keeps_current_engine_active` — 端到端驗證切換失敗後仍可 speak。

### I-2 + I-3 移除 backend 別名與死分支 — 已完成 ✅
全 repo `src` grep `SpeechBackend|speech_backend|selected_backend|backend_options|backend_id|get_speech_backend|set_speech_backend|SpeechBackendChanged|default_speech_backend|on_speech_backend|backend_choices|set_backend\b|get_backend_options` → **僅餘 4 處,均屬可接受**:
1. `SpeechService.single_backend` classmethod(原 review M-7 明文接受,為測試輔助工具,非公開語意 API)。
2. `adapters/windows/clipboard.py` 的 `_get_backend` 屬 Windows clipboard 內部實作,與 speech engine 術語無關。

具體已移除:
- `backends.py`:`SpeechBackendOption`/`SpeechBackendManager`/`selected_backend_id`/`backend_choices`/`set_backend`。
- `application/output/speech/__init__.py`、`application/output/service.py`、`application/output/speech/service.py`、`application/events.py`、`application/config.py` 的別名或 method。
- `bootstrap/platform.py`:`PlatformProvider.default_speech_backend_options/_id` 與模組級 `default_speech_backend_*` 別名。
- `bootstrap/output.py`、`bootstrap/app_runtime.py`:dual-kwargs 與 `or` fallback 已移除。
- `apps/shared/speech_settings_controller.py`:`on_backend_changed` 參數移除。
- 三個 app service 的 `*_speech_backend*` 方法移除。
- `apps/nvda_remote/main.py`:移除所有 `hasattr(...)`/`inspect.signature(...)` 死分支,直接呼叫 engine API;`import inspect` 已不再需要並已移除。
- 測試端 fake 類別的 backend 方法同步遷移。

`apps/key_echo/main.py`(M-3)改用 `selected_engine_id=`/`fallback_engine_id=` 且 id 由 `"pyttsx3"` 改為 `"Pyttsx3"`(符合 plan「Real engine ids should be PascalCase」)。

### I-4 三項整合測試 — 已完成 ✅
新增 `tests/integration/test_speech_engine_persistence_and_routing.py`(217 行,4 個測試),以真實 `SpeechService` + `SpeechEngineConfigStore`(tmp_path) + `RecordingSpeechOutput` 驅動:
1. `test_persisted_engine_and_normalized_values_are_restored_on_restart` — 對應 spec Integration 1:persist → 重啟重建 service → 套用儲存值,驗證引擎/voice/rate/pitch/volume 還原,並斷言 config 只存 normalized percent。
2. `test_per_engine_settings_are_applied_independently_after_switch` — 對應 spec Integration 2:兩引擎各自儲存不同值,切換後確認各引擎套用自身設定,且前引擎 cancel 恰一次。
3. `test_incoming_speech_sequences_route_through_selected_engine_unchanged` — 對應 spec Integration 3:序列路由至當前所選引擎且內容不變。
4. 額外補 `test_engine_switch_failure_keeps_current_engine_active`(I-1 整合層補測)。

測試設計(`_build_engines` 共用 `RecordingSpeechOutput` 物件、`_apply_saved_settings` 鏡射 `main._apply_saved_speech_settings`)良好;無過度 mock,真實走 manager + service。

### M-1 percent helpers 對齊 spec float contract — 已完成 ✅
`src/application/output/speech/settings.py:19-30` 改為:
- `percent_to_range(percent:int, min_value:float, max_value:float) -> float`
- `range_to_percent(raw:float, min_value:float, max_value:float) -> int`

加入 docstring;`pyttsx3.py` 呼叫端改為 `engine.setProperty("rate", round(percent_to_range(...)))`,確保 raw 值仍為 int,與 plan Task 4 文件期望一致,既有 `engine.properties["rate"] == 300` / `["pitch"] == 80` 測試不受影響。

新增測試:
- `test_percent_to_range_returns_float_and_range_to_percent_returns_int`:`isinstance(percent_to_range(50, 50, 300), float)` 與 `range_to_percent` 回傳 int。
- `test_range_to_percent_handles_degenerate_range`:`max==min → 0` 退化範圍保護。

### M-2 拒絕 bool 數值 — 已完成 ✅
`src/application/config.py:34`:`if not isinstance(value, int) or isinstance(value, bool): return None`。
新增測試 `test_speech_engine_config_store_ignores_bool_numeric_settings`:config 寫入 `{"rate": True, "pitch": False}` → 載入均為 None。

### M-3 `key_echo/main.py` 術語 — 已完成 ✅
(見 I-2 區段)

### M-4 移除 `_DEFAULT_ENGINE_OPTIONS` 硬編 — 已完成 ✅
`src/ui/shared/speech_controls.py` 已刪除 `_DEFAULT_ENGINE_OPTIONS` 常數;`_get_speech_engine_options` 改回傳 controller 實際選項(None/無提供時回 `()`);`_get_selected_speech_engine` 對空選項改回 `""` 不再引發 IndexError。引擎知識回歸單一來源(bootstrap/platform)。

### M-5 NVDA percent 映射註明語意 — 已完成 ✅
`src/adapters/windows/nvda_controller.py:225-234` 為 `_normalized_percent_to_ssml_percent` 加入 docstring,說明 baseline 50→`100%`、`value<=0`→`0%`(volume 靜音;rate/pitch 語意由 SSML 引擎決定),並標明此為驅動自留 mapping。

### M-6/M-7 — 不處理 / 保留
M-6(單一 squashed commit)為歷史事實,finish 報告已記錄,未額外造空 commit;同意。
M-7 `SpeechService.single_backend` 測試輔助保留,且 dual-kwargs 已隨 I-2 一併移除,符合 review 期望。

## 2. 因本次修正是否產生新問題?

逐一檢查潛在 regression:

### 2.1 I-1 修正後 `cancel()` 失敗的邊界
順序為 `new_output = create_output()` → `previous.cancel()` → 替換。若 `cancel()` 本身丟例外,`_current_output` 仍指 previous、`selected_engine_id` 不變,符合「保留舊引擎」;副作用是 `new_output` 變孤兒(已建好但未被接管)。對真實驅動(pyttsx3 lazy init、NVDA DLL load)無資源洩漏實質影響;可接受。**無需修正。**

### 2.2 `Pyttsx3SpeechOutput._speak_text` 因 float 改動後的時序
`engine.setProperty("rate", round(percent_to_range(...)))` — `percent_to_range` 現為 float,`round(float)` 回傳 int;既有驅動測試 `engine.properties["rate"] == 300` / `["pitch"] == 80` / `["volume"] == 0.25` 全部仍 pass。**無 regression。**

### 2.3 UI `_get_selected_speech_engine` 回 `""` 對 frame 的影響
`_sync_speech_engine_choice` 邏輯:依 `_speech_engine_options` 找匹配;找不到 → 若有 options 退到第 0 個;無 options 不呼叫 `SetSelection`。`""` 不會與任何 id 相等,只要 controller 正常提供 options 即走第 0 個 fallback,與原行為一致。**無 regression。**

### 2.4 `SpeechService.__init__` 移除 dual-kwargs 是否打破舊呼叫
所有呼叫端(`bootstrap/output.py`、各 `main.py`、測試 fake)均已改用 `engine_options=`/`selected_engine_id=`;`single_backend` classmethod 內部亦用新 kwargs。grep 結果無遺留 `backend_options=` 呼叫。**無 regression。**

### 2.5 `apps/nvda_remote/main.py:_apply_saved_speech_settings` 不再有 `hasattr` 防禦
直接呼叫 `speech.list_voices()`/`speech.get_supported_numeric_settings()`。`tests/unit/test_app_wx.py::FakeBootstrapSpeechOutput` 已新增 `get_supported_numeric_settings` 回 `()`,且對應測試 `test_nvda_remote_main_build_runtime_*` 全 pass。**無 regression。**

### 2.6 `test_app_wx.py` 測試 fake id 仍用小寫 `"pyttsx3"`/`"nvda_controller"`
plan Task 9 明文「Test-local fake ids such as `"default"` may remain where they are not representing the real engines」;此處 fake service id 不代表真引擎出廠 id,小寫保留可接受。**非問題。**

### 2.7 `access8graph/service.py` 的 `SpeechSettingsController` 未含 `on_voice_changed`/`on_numeric_setting_changed`(原本就沒有)
未動現況;access8graph 不持久化 speech 設定,符合既有設計。**非新問題。**

### 2.8 整體測試套件
`587 passed`(unit 573 + integration 14)、無 skipped/error。Speech 相關子集 77 個全 pass。

## 3. 結論

| 項目 | 狀態 |
|---|---|
| I-1 引擎切換失敗保留舊引擎 | ✅ 完成,含 unit + integration 測試 |
| I-2 backend 別名清掃 | ✅ 完成,殘留僅 `single_backend`(接受)與 clipboard 無關 backend |
| I-3 死分支移除 | ✅ 完成,`hasattr`/`inspect.signature` 已絕跡 |
| I-4 整合測試 | ✅ 完成,4 個整合測試涵蓋 spec 三項 + I-1 |
| M-1~M-5 | ✅ 全數完成 |
| M-6/M-7 | ✅ 正確不處理/保留 |
| 新引入 regression | ✅ 未發現 |
| 測試套件 | ✅ 587 passed |

**判定:本修正完成且未引入新問題。可建議使用者將工作區變更提交為一個 commit(例如 `refactor: remove speech backend aliases and harden engine switching` 或依計畫節奏分二~三 commit),再繼續後續流程。**

## 4. 建議提交分組(僅供參考,由使用者決定)

1. `fix: keep current speech engine active when switch factory fails`(I-1 + 對應 unit/integration 測試)
2. `refactor: remove speech backend compatibility aliases and dead branches`(I-2/I-3 + `key_echo/main.py` + 測試遷移)
3. `test: add speech engine persistence and routing integration tests`(I-4)
4. `refactor: align percent helpers and config store with spec`(M-1/M-2/M-5 + 對應測試)
5. `refactor: source speech engine options from controller`(M-4)

或整併為單一 `refactor: address speech engine settings review findings` 亦可。