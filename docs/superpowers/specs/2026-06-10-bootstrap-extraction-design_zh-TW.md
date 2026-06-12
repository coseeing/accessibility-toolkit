# Bootstrap 層抽取設計

## 目的

將共用的平台 adapter 解析與程序級 bootstrap 邏輯從兩個應用程式進入點（`src/apps/nvda_remote/main.py`、`src/apps/key_echo/main.py`）抽取到可重複使用的 `src/bootstrap/` 層。這是更廣泛 SOLID 重構的第一階段，優先處理槓桿效益最高的重複程式碼。

## 範圍

| 包含 | 不包含 |
|------|--------|
| 平台 adapter 解析（輸入擷取、快速鍵、剪貼簿、語音後端選項） | 完整的 provider/registry 模式（延至 Phase 3 輸出架構） |
| 程序啟動（logging 設定、config/log 路徑政策） | 輸出通道重新設計（tone/wave/braille） |
| 消除兩個 main.py 之間的延遲匯入重複 | 拆分 NvdaRemoteAppService（延至 Phase 2） |
| `_NullInputCapture` / `_NullHotkeyCapture` 安全 fallback 供不支援平台使用 | 型別化領域事件（延至 Phase 1 後續） |

## 模組結構

```
src/bootstrap/
  __init__.py
  platform.py    # adapter factory 函式
  runtime.py     # 程序級初始化輔助工具
```

### `platform.py`

僅純函式。所有平台分支（`sys.platform`）與延遲匯入（`importlib.import_module`）均封裝於此。不含任何 class。

**公開 API：**

```python
from adapters.inputs.base import InputCapture, HotkeyCapture
from application.services import ClipboardService
from application.output_scheduler import OutputScheduler
from application.speech_backends import SpeechBackendOption

def create_input_capture() -> InputCapture: ...
def create_hotkey_capture() -> HotkeyCapture: ...
def create_clipboard_service() -> ClipboardService: ...
def default_speech_backend_options(scheduler: OutputScheduler) -> tuple[SpeechBackendOption, ...]: ...
def default_speech_backend_id() -> str: ...
```

**內部設計：**

- macOS 的 `InputCapture` 與 `HotkeyCapture` 透過模組級延遲初始化快取（`_macos_event_tap_manager`）共用同一個 `EventTapManager` 實例。
- 所有 adapter class 均透過私有 `_get_*` 函式以模組級全域快取變數進行延遲匯入（與目前 main.py 模式相同）。
- 平台偵測使用單一 `_PLATFORM = sys.platform` 常數。

**各能力的 fallback 行為：**

| 能力 | Windows | macOS | 其他 |
|------|---------|-------|------|
| InputCapture | `WindowsKeyboardCapture()` | `MacOSKeyboardCapture(manager)` | `_NullInputCapture()` |
| HotkeyCapture | `WindowsHotkeyCapture()` | `MacOSHotkeyCapture(manager)` | `_NullHotkeyCapture()` |
| ClipboardService | `WindowsClipboardService()` | `_UnsupportedClipboardService()` | `_UnsupportedClipboardService()` |
| SpeechBackendOption | nvda_controller + pyttsx3 | 僅 pyttsx3 | 僅 pyttsx3 |

`_NullInputCapture` 與 `_NullHotkeyCapture` 實作各自的協定，`start()` 時記錄 warning 而非崩潰。`_UnsupportedClipboardService` 從 `nvda_remote/main.py` 移至 `platform.py`（它本來就是通用的 fallback）。

### `runtime.py`

程序級初始化。不依賴任何平台 adapter 或應用程式服務。

**公開 API：**

```python
from pathlib import Path

def configure_logging(log_path: Path | None = None, app_name: str = "nvda-remote-client") -> Path: ...
def default_log_path(app_name: str = "nvda-remote-client") -> Path: ...
def default_config_path(app_name: str = "nvda-remote-client") -> Path: ...
```

**路徑政策（與目前行為一致，未變更）：**

- Frozen + macOS：`~/Library/Logs/{app_name}/{app_name}.log`、`~/Library/Application Support/{app_name}/{app_name}.json`
- Frozen + 其他平台：`{sys.executable.parent}/{app_name}.log`、`{sys.executable.parent}/{app_name}.json`
- 開發模式（未 frozen）：`{cwd}/{app_name}.log`、`{cwd}/{app_name}.json`

**`configure_logging` 行為（與目前一致）：**
- 在 log_path 建立 DEBUG 等級的檔案 handler，使用標準格式
- 若檔案 logging 失敗則退回到主控台 logging
- 回傳所使用的 log_path

## 遷移計畫

1. 建立 `src/bootstrap/__init__.py`、`platform.py`、`runtime.py`
2. 改寫 `nvda_remote/main.py` 的 `build_runtime()` 以使用 `platform.py` / `runtime.py`
3. 改寫 `key_echo/main.py` 的 `build_runtime()` 以使用 `platform.py`
4. 從兩個 main.py 檔案中刪除所有重複的輔助工具：
   - 延遲匯入輔助工具（`_get_windows_*_class`、`_get_nvda_controller_*`、`_get_macos_*`、`_load_macos_*`）
   - `_build_input_adapters`、`_build_clipboard_service`、`_build_macos_event_tap_manager`
   - `_default_backend_options`、`default_log_path`、`default_config_path`、`configure_logging`
   - 模組級全域延遲快取變數
5. 執行 `pytest tests/unit tests/integration -v`

## 保留在 main.py 的內容

- `NvdaRemoteRuntime` / `KeyEchoRuntime` dataclass（app 專屬）
- `build_runtime()` 函式（app 專屬 wiring，但改為呼叫 bootstrap 取得 adapter）
- `main()` entrypoint
- `_is_frozen()` 輔助工具（移至 `runtime.py` 作為私有函式）

## 不變更的內容

- `SpeechBackendConfigStore` 保留在 `application/config.py`
- `NvdaRemoteAppService` / `KeyEchoAppService` 保留在各自的 service.py 檔案
- `OutputScheduler`、`SpeechService`、`QueuedOutputService` 保留在 `application/` 目錄
- `KeyboardInputService` 保留在 `application/keyboard.py`
- `adapters/windows/` 與 `adapters/macos/` 中的所有 adapter 實作均不變更
- `adapters/inputs/base.py` 中的 `InputCapture` / `HotkeyCapture` 協定均不變更

## 後續演進路徑

此設計為後續階段建立了乾淨的接縫：

- `platform.py` 的函式可在 Phase 3（輸出通道）演進為 `PlatformAdapterProvider` class
- `runtime.py` 可吸收任何未來的跨應用程式啟動需求
- `_Null*` fallback 為未來平台擴展（例如 Linux）提供了 pattern
