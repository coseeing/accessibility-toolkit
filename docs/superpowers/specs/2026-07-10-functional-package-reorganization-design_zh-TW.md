# Accessibility Toolkit 功能導向 Package 重構設計

## 概述

本重構將 `accessibility_toolkit` 從技術分層導向的目錄結構，改為以 accessibility application 使用者可辨識的功能領域組織。目標是讓套件使用者依其要完成的工作找到 API，例如輸入、輸出、排程、互動、事件與遠端連線，而不必先理解 `application`、`interop` 或 `adapters` 等內部架構名詞。

本次是一次完整的 breaking refactor。所有原有路徑會移除；不建立 compatibility shim、deprecated re-export 或暫時 façade。repository 內的 app、UI、測試、文件與 packaging 設定都必須在同一次變更中改用新路徑。

## 背景與問題

目前一個「處理鍵盤輸入」的功能分散在三種技術層：

- `interop.key`：`KeyEvent`、`HID` 等資料模型。
- `adapters.inputs`、`adapters.windows`、`adapters.macos`：擷取介面與平台實作。
- `application.input`：輸入管線、policy 與 service。

這個安排有利於描述內部依賴，但對套件使用者而言，使用同一項功能時必須跨越多個抽象層尋找類別。相同問題也存在於 speech/output、mode lifecycle 與 remote protocol。

## 目標

- 以功能領域作為 `accessibility_toolkit` 的第一層 package 邊界。
- 讓一般使用者可從 `input`、`output`、`scheduling`、`interaction`、`events`、`remote` 與 `runtime` 找到 API。
- 將平台實作置於其所服務的功能之下，不再保留全域 `adapters` package。
- 將目前 output 專用位置的 scheduler 升格為可同時服務 input 與 output 的中性基礎能力。
- 保持既有執行行為與各 app 功能不變；此重構的主要變更是 package 邊界、imports 與公開 API。
- 讓 `accessibility-toolkit-core` 僅發行 core Python namespace，不包含 wx package。

## 非目標

- 不在本次新增 input scheduling 行為，例如 debounce、repeat-key 合併或延遲 command；只建立其未來可共用的 package 邊界。
- 不改變 keyboard pipeline、speech queue、relay protocol 或 mode 行為。
- 不將 `remote` 從 core 拆成獨立 distribution package。
- 不搬動 `accessibility_toolkit_wx` 的 UI 結構；它持續是獨立的 UI package。
- 不以新的通用 EventBus 取代既有 typed events。

## 設計原則

### 功能優先於實作分層

第一層 package 名稱必須回答「使用者要做什麼」，而非「這段程式在架構的哪一層」。內部檔案仍可有 ports、drivers 或平台細節，但它們應位於所屬功能的 package 內。

### 平台實作歸屬於功能

Windows/macOS keyboard hook 是 input；NVDA Controller 與 pyttsx3 是 output speech；clipboard 是 output。它們不再集中於全域 `adapters`，以免使用者先選平台、而不是先選能力。

### event 不作為資料模型垃圾桶

事件應留在所屬領域：鍵盤事件在 `input.events`，relay protocol events 在 `remote.events`。根層 `events` 僅收納跨功能、對 application/UI 有意義的 lifecycle events，例如 mode、capture、engine 與 error 狀態變更。

### scheduling 是中性基礎能力

`Scheduler` 目前的第一個 consumer 是 output，但未來 input 也會需要可排程、可取消或延遲處理的工作。`scheduling` 的 API、型別、參數與文件不得綁定 speech 或 output 語意。

### remote 保留在 core

remote 目前保留為 core 的功能模組。它必須保持自包含，且 `input`、`output`、`scheduling`、`interaction` 與 `events` 不得反向依賴 `remote`。app 可選擇結合 remote 與其他功能。此規則使未來抽出獨立 distribution package 時只需處理 `remote` 的依賴。

## 目標目錄結構

```text
src/accessibility_toolkit/
  input/
    __init__.py
    hid.py
    events.py
    capture.py
    activation.py
    pipeline.py
    policies.py
    results.py
    service.py
    windows/
      __init__.py
      hid_map.py
      hotkey.py
      keyboard_hook.py
      native_key_context.py
    macos/
      __init__.py
      event_tap.py
      hid_map.py
      hotkey.py
      keyboard_hook.py
      keymap.py
      permissions.py

  output/
    __init__.py
    queue.py
    capabilities.py
    clipboard.py
    interfaces.py
    ports.py
    tone.py
    wave.py
    braille.py
    windows/
      __init__.py
      clipboard.py
    speech/
      __init__.py
      commands.py
      sequence.py
      null.py
      service.py
      settings.py
      settings_store.py
      json_settings_store.py
      runtime_settings.py
      settings_facade.py
      backends.py
      drivers/
        __init__.py
        pyttsx3.py
      windows/
        __init__.py
        nvda_controller.py
        vendor/

  scheduling/
    __init__.py
    scheduler.py

  interaction/
    __init__.py
    modes.py

  events/
    __init__.py
    application.py

  remote/
    __init__.py
    connection.py
    messages.py
    serializer.py
    events.py
    routing/
      __init__.py
      message_router.py
    session/
      __init__.py
      remote_session.py
    transport/
      __init__.py
      base.py
      relay.py

  runtime/
    __init__.py
    environment.py
    platform.py
    output.py
    runtime_parts.py
```

`windows/` 與 `macos/` 是功能 package 的子目錄；其 `__init__.py` 應只 export 該功能在該平台所支援的實作。平台共用但不屬於單一功能的 runtime 選擇邏輯維持在 `runtime.platform`。

NVDA Controller driver 擁有其 vendored DLL，並使用 `Path(__file__)` 相對於 `output/speech/windows/nvda_controller.py` 定位資源；不得為了尋找資源而 import `runtime.environment`。PyInstaller 必須保留相同的 package-relative `vendor/nvda/x64` 配置，使 source、安裝後的 wheel 與 frozen application 都使用同一種定位方式。

## 功能邊界

### `input`

負責從平台取得輸入、將輸入正規化、管理 capture lifecycle，以及執行共享 keyboard pipeline。

公開概念包含：

- `HID`、`KeyEvent`、`CapturedKeyEvent`
- `InputCapture`、`HotkeyCapture`
- `KeyboardInputService`、`KeyEventHandler`
- `InputActivationUseCase`
- `KeyboardPipelineResult`、`AppKeyEventResult`
- active-key 與 system-toggle policy
- Windows/macOS keyboard hook、hotkey、HID mapping 與 macOS input permission 實作

input 不處理 app 特有的 command 語意，亦不負責 speech 或其他回饋。

### `output`

負責將 application 的回饋請求呈現給使用者，包括 speech、tone、wave、braille 與 clipboard。

公開概念包含：

- `QueuedService` 與其 output mode
- `Capabilities`、speech ports 與 output interfaces
- `ClipboardService`
- `SpeechService`、speech backend、settings 與 settings store
- `SpeechRuntimeSettingsCoordinator` 與 `SpeechSettingsFacade`
- `JsonSpeechSettingsStore`
- `SpeechSequence`、speech commands
- tone、wave、braille output
- pyttsx3 與 Windows NVDA Controller 實作

輸出的工作順序與取消機制使用 `scheduling`，但 `output` 不擁有 scheduler 的實作。

### `scheduling`

負責通用的可排隊、可取消、可等待完成與可設定 timeout 的工作執行。

公開概念包含：

- `Scheduler`
- `CancellationToken`
- `ScheduledFuture`
- `EventCallbacks`

第一個 consumer 是 output speech queue 與 backend；未來 input 可使用同一 API 實作 debounce、repeat-key 聚合、延遲觸發或可取消處理。此 package 不得 import `input`、`output`、`interaction` 或 `remote`。

### `interaction`

負責 accessibility application 的無 UI 互動情境、狀態與規則。它回答的是「此刻此輸入代表什麼，以及系統應如何切換互動狀態」，而不是「如何取得按鍵」或「如何說出內容」。

本次包含：

- `ModeManager` 與 mode 型別
- mode 進入、離開、切換與 rollback 所需的共用 lifecycle 協調

未來可包含共用 command routing 或 interaction/session state；不得放入平台 hooks、speech drivers、wx UI 或 app 專屬導航規則。

### `events`

負責跨功能、對 application 與 UI 有意義的 typed lifecycle events。

本次包含：

- `ErrorRaised`
- `SpeechEngineChanged`
- `InputCaptureChanged`
- `HotkeyCaptureChanged`
- `ClipboardAvailabilityChanged`
- `ModeChanged`
- `AppEvent`

鍵盤資料事件不移入此處，維持在 `input.events`；remote protocol events 維持在 `remote.events`。

### `remote`

負責 relay protocol、序列化、transport、session 與 message routing。它可被 app 使用，但 core 的其他功能 package 不得依賴它。

公開概念包含：

- connection information 與 remote messages
- protocol serializer 與 events
- message router
- `RemoteSession`
- transport interfaces 與 relay transport

### `runtime`

負責 application composition、環境設定、平台選擇與共享 runtime parts。它是組裝層，允許依賴各功能 package；功能 package 不得反向依賴 runtime。

## 既有檔案搬遷對照

| 現有位置 | 目標位置 |
|---|---|
| `interop/key/*` | `input/events.py` 或 `input/` 對應模組 |
| `adapters/inputs/*` | `input/capture.py`、`input/events.py` |
| `adapters/windows/{keyboard_hook,hotkey,hid_map,native_key_context}.py` | `input/windows/` |
| `adapters/macos/{event_tap,keyboard_hook,hotkey,hid_map,keymap,permissions}.py` | `input/macos/` |
| `application/input/*` | `input/{activation,pipeline,policies,...}.py` |
| `application/output/scheduler.py` | `scheduling/scheduler.py` |
| `application/output/{service,capabilities,ports,clipboard}.py` | `output/` 對應模組 |
| `interop/speech/*` | `output/speech/{commands,sequence}.py` |
| `application/output/speech/*` | `output/speech/` 對應模組 |
| `application_support/{speech_runtime_settings,speech_settings_facade}.py` | `output/speech/{runtime_settings,settings_facade}.py` |
| `adapters/config/json_speech_settings.py` | `output/speech/json_settings_store.py` |
| `adapters/outputs/*` | `output/` 或 `output/speech/` 對應模組 |
| `adapters/outputs/ref𦳒.txt` | 刪除；這是沒有 repository consumer、不可 import 的未使用參考檔 |
| `adapters/windows/clipboard.py` | `output/windows/clipboard.py` |
| `adapters/windows/nvda_controller.py` 與 vendored DLL | `output/speech/windows/nvda_controller.py` 與 `output/speech/windows/vendor/` |
| `application_support/{mode_manager,mode_types}.py` | `interaction/modes.py` |
| `application/events.py` | `events/application.py` |
| `interop/protocol/*` | `remote/` 對應模組 |
| `runtime/*` | 保持 `runtime/`，只更新 imports |

實作時可依單一功能的既有檔案數量保留多個檔案；上表中的合併檔名是功能歸屬，不要求為了搬遷而合併邏輯。

## 公開 API

每個第一層功能 package，以及公開的 `output.speech`、`input.windows`、`input.macos`、`remote.routing`、`remote.session` 與 `remote.transport` 子 package，都必須在 `__init__.py` 定義明確、穩定的 public API 與顯式 `__all__`。一般使用情境不應需要 import 私有或實作導向路徑。Driver module 與 vendored-resource 目錄屬於實作路徑，不要求由 root package re-export。

預期使用形式：

```python
from accessibility_toolkit.input import KeyEvent, KeyboardInputService
from accessibility_toolkit.input.windows import WindowsKeyboardHook
from accessibility_toolkit.output import QueuedService
from accessibility_toolkit.output.speech import SpeechSequence, SpeechService
from accessibility_toolkit.scheduling import Scheduler
from accessibility_toolkit.interaction import ModeManager
from accessibility_toolkit.remote import RemoteSession
```

具平台或 driver 性質的 import 可使用功能底下的實作路徑；例如 `output.speech.drivers.pyttsx3`。不得要求使用者先透過 `adapters` 尋找該能力。

## 依賴規則

```text
output ──────────────> scheduling
interaction ─────────> input, events
remote ──────────────> output.speech（wire-format speech models）
runtime ─────────────> input, output, scheduling, interaction, events, remote

input ··············> scheduling（未來允許的依賴；本次重構不建立）
```

- `scheduling` 不依賴任何功能 package。
- `events` 不依賴任何功能 package。
- `remote` 不得被其他 core 功能 package 依賴。
- `remote` 可依賴現有 wire format 所需的穩定 `output.speech` command 與 sequence models；output 不得依賴 remote。
- `runtime` 可以組裝所有功能，但不得被功能 package 依賴。
- NVDA Controller driver 必須自行定位其 package 擁有的 DLL，不得 import `runtime`。
- `accessibility_toolkit_wx` 可依賴 core 的 public API；core 不得依賴 wx。
- app 專屬 domain 邏輯留在 `apps/*`，不因重構移入 toolkit。

## 破壞性遷移規則

- 刪除 `application/`、`application_support/`、`interop/` 與 `adapters/` package。
- 不建立舊路徑的 re-export、import forwarding、警告或 compatibility module。
- 更新 `src/apps`、`src/ui`、`tests` 與文件中的每一個 import。
- 使用 ripgrep 驗證下列舊 namespace 在 source 與 tests 中均不再作為可用 import 出現：`accessibility_toolkit.application`、`accessibility_toolkit.application_support`、`accessibility_toolkit.interop`、`accessibility_toolkit.adapters`。歷史文件只有在明確描述舊架構時才可提及它們。

## Packaging 與文件

`packages/accessibility-toolkit-core/pyproject.toml` 的 package discovery 必須從寬鬆的 `accessibility_toolkit*` 改為只包含：

```toml
include = ["accessibility_toolkit", "accessibility_toolkit.*"]
```

這可避免 `accessibility_toolkit_wx` 因為相同前綴而被 core distribution 收錄。

core package metadata 與 root development package metadata 的 package-data 宣告都必須改指向 `accessibility_toolkit.output.speech.windows` 及新的 `vendor/nvda/x64/*.dll` 位置。`packaging/windows_apps.spec` 必須同步更新 DLL 來源／目的地與 hidden-import module paths。Packaging 不得保留任何指向已移除 `adapters` tree 的設定。

README 與架構文件必須以新功能 package 結構取代已過時的 `application/interop/adapters/bootstrap` 圖示，並新增從 input、output、scheduling 開始的簡短使用範例。

## 驗收條件

- `src/accessibility_toolkit` 僅保留本 spec 定義的功能導向第一層 package 與 root `__init__.py`。
- 不存在 `accessibility_toolkit.application`、`application_support`、`interop` 或 `adapters` 目錄與可 import module。
- app、UI、unit tests 與 integration tests 均使用新 import paths 並通過。
- `Scheduler` 位於 `accessibility_toolkit.scheduling`，且不依賴 output 或 input。
- 本 spec 指定的每個第一層功能 package 與公開巢狀 package 均有明確 `__init__.py` 與 `__all__` public API。
- `remote` 位於 core，且除 runtime 與 app 外，其他 core 功能 package 不 import remote。
- core 功能 package 不 import `runtime`；NVDA Controller driver 尤其必須從自己的 package 目錄定位 DLL。
- `accessibility-toolkit-core` 的 wheel/sdist 不包含 `accessibility_toolkit_wx`。
- Windows executable spec 與 Python package metadata 會從新的 output/speech 位置收錄 NVDA Controller DLL。
- README、中文 README、spec 與 package migration 文件反映新結構。

## 驗證

至少執行：

```bash
python -c "import accessibility_toolkit"
pytest tests/unit tests/integration -v
rg -n "^(from|import) accessibility_toolkit\.(application|application_support|interop|adapters)" src tests
rg -n "adapters[./]|accessibility_toolkit\.adapters" packages packaging pyproject.toml
```

最後兩個命令不應發現任何指向已移除 namespace 的有效 import、package-data path、hidden import 或 bundled-file path。歷史設計文件若明確標示為舊架構記錄，仍可保留相關描述。
