# Fix: Wire speech engine persistence callbacks for key_echo and access8graph

Both `key_echo` and `access8graph` use `SpeechSettingsFrame` via `ToolAppShell` but
their `SpeechSettingsController` is created without `on_engine_changed`/`on_voice_changed`/
`on_numeric_setting_changed` callbacks. Changes in the speech settings panel apply to the
active engine but are never persisted. Also neither app loads saved settings on startup.

This plan aligns them with `nvda_remote`'s approach: `SpeechEngineConfigStore` +
callbacks + startup loading.

## File 1: `src/apps/key_echo/service.py`

```
1. Add `from collections.abc import Callable` before line 1
2. In `__init__`:
   - Add parameters (after `capabilities`, before `main_thread_dispatch`):
       on_speech_engine_changed: Callable[[str], None] | None = None,
       on_voice_changed: Callable[[str, str], None] | None = None,
       on_numeric_setting_changed: Callable[[str, str, int], None] | None = None,
   - Change `SpeechSettingsController(speech=capabilities.speech)` to:
       SpeechSettingsController(
           speech=capabilities.speech,
           on_engine_changed=on_speech_engine_changed,
           on_voice_changed=on_voice_changed,
           on_numeric_setting_changed=on_numeric_setting_changed,
       )
```

## File 2: `src/apps/access8graph/service.py`

Same three changes: import `Callable`, three callback params, pass to `SpeechSettingsController`.

## File 3: `src/apps/key_echo/main.py`

| Change | Detail |
|---|---|
| Import | Add `from application.config import SpeechEngineConfigStore` |
| Import | Add `from bootstrap.runtime import default_config_path` |
| Runtime dataclass | Add `config_store: SpeechEngineConfigStore` field |
| `build_runtime()` | Add `config_store = SpeechEngineConfigStore(default_config_path())` at top |
| `build_runtime()` | Define `_apply_saved_speech_settings(speech, engine_id)` helper (copy from nvda_remote) |
| `build_runtime()` | After building `parts`, call `_apply_saved_speech_settings(parts.output.speech, "Pyttsx3")` |
| `build_runtime()` | Define `_on_speech_engine_changed(engine_id)` that saves engine_id + reapplies settings |
| `build_runtime()` | Pass `on_speech_engine_changed=_on_speech_engine_changed, on_voice_changed=config_store.save_voice, on_numeric_setting_changed=config_store.save_numeric_setting` to `KeyEchoAppService(...)` |
| Return | Add `config_store=config_store` to `KeyEchoRuntime(...)` |

## File 4: `src/apps/access8graph/main.py`

Same as key_echo but:
- `selected_engine_id` comes from `config_store.load_engine_id(default_engine_id=...)` 
  with PlatformProvider (mirrors nvda_remote)
- Pass `selected_engine_id` to `build_app_runtime_parts`
- Add `Access8GraphRuntime` field `config_store`

## File 5: `tests/unit/test_key_echo_app_service.py`

- `install_fake_key_echo_runtime_parts`'s `fake_build_app_runtime_parts` must also pass
  `on_engine_fallback` to kwargs check (currently asserts `kwargs == {}`)
- Add `KeyEchoRuntime` fake `config_store` attribute expectations

## Verification

```bash
python3 -m pytest tests/unit/test_key_echo_app_service.py tests/unit/test_access8graph_app_service.py tests/unit/test_app_wx.py -v
python3 -m pytest tests/unit tests/integration -q
```
