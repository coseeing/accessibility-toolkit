# Toolkit 套件遷移實作 Checklist

> **狀態：已完成並被取代**
>
> 此 checklist 已被功能導向套件重組所取代。舊的技術層套件（`application`、`interop`、`adapters`、`bootstrap`、`apps/shared`）已重組為 `accessibility_toolkit` 下的 7 個功能導向套件：`input`、`output`/`output.speech`、`scheduling`、`interaction`、`events`、`remote` 與 `runtime`。
>
> 請參閱新結構的設計與實作文件：
> - `docs/superpowers/specs/2026-07-10-functional-package-reorganization-design.md`
> - `docs/superpowers/plans/2026-07-10-functional-package-reorganization-implementation.md`

## 目的（歷史記錄）

這份 checklist 將 `toolkit-package-migration-plan.md` 拆成可逐步執行的實作工作。目標是在不改變既有 app 行為的前提下，將共用功能整理成可獨立發佈的套件：

- `accessibility-toolkit-core`
- `accessibility-toolkit-wx`

本文件採用 `accessibility_toolkit.application_support` 作為支援層 namespace。

## 執行原則

- [ ] 每一批搬移都先保持行為不變。
- [ ] 每一批搬移後都執行最小相關測試。
- [ ] 新 namespace 穩定後再更新 app imports。
- [ ] 舊路徑用 compatibility shim 過渡，等 app imports 全部改完後再移除。
- [ ] toolkit package 不得 import `apps.*` 或 app-specific `ui.*`。
- [ ] `accessibility-toolkit-core` 不得依賴 `wxPython`。

## Phase 0：決策凍結

- [ ] 確認 core distribution 名稱為 `accessibility-toolkit-core`。
- [ ] 確認 core Python namespace 為 `accessibility_toolkit`。
- [ ] 確認 UI distribution 名稱為 `accessibility-toolkit-wx`。
- [ ] 確認 UI Python namespace 為 `accessibility_toolkit_wx`。
- [ ] 確認 `bootstrap` 搬移後命名為 `accessibility_toolkit.runtime`。
- [ ] 確認 app 支援層命名為 `accessibility_toolkit.application_support`。
- [ ] 確認 `speech_settings_facade` 先放在 `accessibility_toolkit.application_support`，若日後證明只服務 wx UI 再移到 `accessibility_toolkit_wx`。

驗證：

```bash
rg -n "app_support|application_support" docs
```

## Phase 1：建立新 namespace 骨架

- [ ] 建立 `src/accessibility_toolkit/__init__.py`。
- [ ] 建立 `src/accessibility_toolkit/application/`。
- [ ] 建立 `src/accessibility_toolkit/interop/`。
- [ ] 建立 `src/accessibility_toolkit/adapters/`。
- [ ] 建立 `src/accessibility_toolkit/runtime/`。
- [ ] 建立 `src/accessibility_toolkit/application_support/`。
- [ ] 建立 `src/accessibility_toolkit_wx/__init__.py`。
- [ ] 建立 `src/accessibility_toolkit_wx/shell/`。
- [ ] 建立 `src/accessibility_toolkit_wx/speech/`。
- [ ] 建立 `src/accessibility_toolkit_wx/tray/`。

驗證：

```bash
PYTHONPATH=src python -c "import accessibility_toolkit; import accessibility_toolkit_wx"
```

## Phase 2：搬移 core 模組

### 2.1 搬移 `application`

- [ ] 搬移 `src/application/**` 到 `src/accessibility_toolkit/application/**`。
- [ ] 更新新位置內部 import，將 `application.` 改為 `accessibility_toolkit.application.`。
- [ ] 更新新位置內部 import，將 `interop.` 改為 `accessibility_toolkit.interop.`。
- [ ] 更新新位置內部 import，將 `adapters.` 改為 `accessibility_toolkit.adapters.`。
- [ ] 在舊 `src/application/**` 建立 compatibility shim。

建議驗證：

```bash
PYTHONPATH=src pytest tests/unit/test_application_events.py tests/unit/test_keyboard_input_service.py tests/unit/test_output_service.py -v
```

### 2.2 搬移 `interop`

- [ ] 搬移 `src/interop/**` 到 `src/accessibility_toolkit/interop/**`。
- [ ] 更新新位置內部 import，將 `interop.` 改為 `accessibility_toolkit.interop.`。
- [ ] 在舊 `src/interop/**` 建立 compatibility shim。

建議驗證：

```bash
PYTHONPATH=src pytest tests/unit/test_hid_keys.py tests/unit/test_protocol_serializer.py tests/unit/test_remote_session.py tests/unit/test_speech_commands.py -v
```

### 2.3 搬移 `adapters`

- [ ] 搬移 `src/adapters/**` 到 `src/accessibility_toolkit/adapters/**`。
- [ ] 確認 `src/adapters/windows/vendor/nvda/x64/nvdaControllerClient.dll` 已搬到新 package data 路徑。
- [ ] 更新新位置內部 import，將 `adapters.` 改為 `accessibility_toolkit.adapters.`。
- [ ] 更新新位置內部 import，將 `application.` 改為 `accessibility_toolkit.application.`。
- [ ] 更新新位置內部 import，將 `interop.` 改為 `accessibility_toolkit.interop.`。
- [ ] 保留 Windows 與 macOS adapter 的 lazy import 行為。
- [ ] 在舊 `src/adapters/**` 建立 compatibility shim。

建議驗證：

```bash
PYTHONPATH=src pytest tests/unit/test_windows_adapters.py tests/unit/test_macos_adapters.py tests/unit/test_json_speech_settings_store.py tests/unit/test_tone_output.py -v
```

### 2.4 搬移 `bootstrap` 到 `runtime`

- [ ] 搬移 `src/bootstrap/runtime.py` 到 `src/accessibility_toolkit/runtime/runtime.py`，或重新命名為更清楚的 module。
- [ ] 搬移 `src/bootstrap/output.py` 到 `src/accessibility_toolkit/runtime/output.py`。
- [ ] 搬移 `src/bootstrap/platform.py` 到 `src/accessibility_toolkit/runtime/platform.py`。
- [ ] 搬移 `src/bootstrap/app_runtime.py` 到 `src/accessibility_toolkit/runtime/app_runtime.py`。
- [ ] 更新新位置內部 import，改用 `accessibility_toolkit.*`。
- [ ] 在舊 `src/bootstrap/**` 建立 compatibility shim。

建議驗證：

```bash
PYTHONPATH=src pytest tests/unit/test_bootstrap_runtime.py tests/unit/test_bootstrap_output.py tests/unit/test_bootstrap_platform.py tests/unit/test_bootstrap_app_runtime.py -v
```

## Phase 3：搬移 `apps/shared` 到 application support

- [ ] 搬移 `src/apps/shared/mode_manager.py` 到 `src/accessibility_toolkit/application_support/mode_manager.py`。
- [ ] 搬移 `src/apps/shared/speech_runtime_settings.py` 到 `src/accessibility_toolkit/application_support/speech_runtime_settings.py`。
- [ ] 搬移 `src/apps/shared/speech_settings_facade.py` 到 `src/accessibility_toolkit/application_support/speech_settings_facade.py`。
- [ ] 建立 `src/accessibility_toolkit/application_support/__init__.py` 並 re-export public classes。
- [ ] 更新新位置內部 import，改用 `accessibility_toolkit.application.*`。
- [ ] 在舊 `src/apps/shared/**` 建立 compatibility shim。

建議驗證：

```bash
PYTHONPATH=src pytest tests/unit/test_mode_manager.py tests/unit/test_speech_runtime_settings.py tests/unit/test_speech_settings_facade.py -v
```

## Phase 4：搬移 `ui/shared` 到 `accessibility_toolkit_wx`

- [ ] 搬移 `src/ui/shared/panel_controller.py` 到 `src/accessibility_toolkit_wx/shell/panel_controller.py`。
- [ ] 搬移 `src/ui/shared/tool_app_shell.py` 到 `src/accessibility_toolkit_wx/shell/tool_app_shell.py`。
- [ ] 搬移 `src/ui/shared/tray_icon.py` 到 `src/accessibility_toolkit_wx/tray/tray_icon.py`。
- [ ] 搬移 `src/ui/shared/speech_controls.py` 到 `src/accessibility_toolkit_wx/speech/speech_controls.py`。
- [ ] 搬移 `src/ui/shared/speech_settings_frame.py` 到 `src/accessibility_toolkit_wx/speech/speech_settings_frame.py`。
- [ ] 建立 `src/accessibility_toolkit_wx/shell/__init__.py`。
- [ ] 建立 `src/accessibility_toolkit_wx/speech/__init__.py`。
- [ ] 建立 `src/accessibility_toolkit_wx/tray/__init__.py`。
- [ ] 更新新位置內部 import，改用 `accessibility_toolkit_wx.*`。
- [ ] 在舊 `src/ui/shared/**` 建立 compatibility shim。

建議驗證：

```bash
PYTHONPATH=src pytest tests/unit/test_panel_controller.py tests/unit/test_tool_app_shell.py tests/unit/test_tray_icon.py tests/unit/test_app_wx.py -v
```

## Phase 5：更新 app imports

### 5.1 更新 app service imports

- [ ] 將 `apps.nvda_remote.service` 中的 `apps.shared.mode_manager` 改為 `accessibility_toolkit.application_support.mode_manager`。
- [ ] 將 `apps.key_echo.service` 中的 `apps.shared.mode_manager` 改為 `accessibility_toolkit.application_support.mode_manager`。
- [ ] 將 `apps.access8graph.service` 中的 `apps.shared.mode_manager` 改為 `accessibility_toolkit.application_support.mode_manager`。
- [ ] 將 app service 中的 `application.*`、`interop.*`、`adapters.*` imports 改為 `accessibility_toolkit.*`。

### 5.2 更新 app runtime imports

- [ ] 更新 `src/apps/nvda_remote/main.py` imports。
- [ ] 更新 `src/apps/key_echo/main.py` imports。
- [ ] 更新 `src/apps/access8graph/main.py` imports。
- [ ] 將 `apps.shared.speech_runtime_settings` 改為 `accessibility_toolkit.application_support.speech_runtime_settings`。
- [ ] 將 `apps.shared.speech_settings_facade` 改為 `accessibility_toolkit.application_support.speech_settings_facade`。
- [ ] 將 `bootstrap.*` 改為 `accessibility_toolkit.runtime.*`。

### 5.3 更新 app UI imports

- [ ] 將 `ui.nvda_remote.app` 的 `ui.shared.*` imports 改為 `accessibility_toolkit_wx.*`。
- [ ] 將 `ui.echo.app` 的 `ui.shared.*` imports 改為 `accessibility_toolkit_wx.*`。
- [ ] 將 `ui.access8graph.app` 的 `ui.shared.*` imports 改為 `accessibility_toolkit_wx.*`。
- [ ] 將 app-specific UI 中的 `application.*` imports 改為 `accessibility_toolkit.application.*`。

建議驗證：

```bash
PYTHONPATH=src pytest tests/unit/test_nvda_remote_app_service.py tests/unit/test_key_echo_app_service.py tests/unit/test_access8graph_app_service.py -v
PYTHONPATH=src pytest tests/unit/test_nvda_remote_use_cases.py tests/unit/test_key_echo_use_cases.py tests/unit/test_access8graph_use_cases.py -v
```

## Phase 6：更新 tests imports

- [ ] 將 unit tests 中的 `application.*` imports 改為 `accessibility_toolkit.application.*`。
- [ ] 將 unit tests 中的 `interop.*` imports 改為 `accessibility_toolkit.interop.*`。
- [ ] 將 unit tests 中的 `adapters.*` imports 改為 `accessibility_toolkit.adapters.*`。
- [ ] 將 unit tests 中的 `bootstrap.*` imports 改為 `accessibility_toolkit.runtime.*`。
- [ ] 將 unit tests 中的 `apps.shared.*` imports 改為 `accessibility_toolkit.application_support.*`。
- [ ] 將 unit tests 中的 `ui.shared.*` imports 改為 `accessibility_toolkit_wx.*`。
- [ ] 保留 app-specific tests 對 `apps.*` 與 app-specific `ui.*` 的 imports。

搜尋檢查：

```bash
rg -n "from (application|interop|adapters|bootstrap|apps\.shared|ui\.shared)|import (application|interop|adapters|bootstrap|apps\.shared|ui\.shared)" tests src
```

建議驗證：

```bash
PYTHONPATH=src pytest tests/unit -v
```

## Phase 7：建立 package metadata

### 7.1 建立 monorepo package 目錄

- [ ] 建立 `packages/accessibility-toolkit-core/`。
- [ ] 建立 `packages/accessibility-toolkit-wx/`。
- [ ] 決定是否立即搬移 source 到 `packages/*/src`，或先維持 `src/` namespace layout。

建議：第一輪先完成 namespace 遷移，再拆 source root 到 `packages/`，降低同時變更的範圍。

### 7.2 建立 `accessibility-toolkit-core` metadata

- [ ] 建立 `packages/accessibility-toolkit-core/pyproject.toml`。
- [ ] 設定 package name 為 `accessibility-toolkit-core`。
- [ ] 設定 package-dir 指向 core source。
- [ ] 設定 package discovery 只包含 `accessibility_toolkit*`。
- [ ] 宣告 `pyttsx3` dependency。
- [ ] 宣告 macOS `pyobjc` dependencies 與 `sys_platform == "darwin"` marker。
- [ ] 宣告 NVDA DLL package data。
- [ ] 確認 `pyinstaller` 不在 runtime dependencies。
- [ ] 確認 `wxPython` 不在 core dependencies。

### 7.3 建立 `accessibility-toolkit-wx` metadata

- [ ] 建立 `packages/accessibility-toolkit-wx/pyproject.toml`。
- [ ] 設定 package name 為 `accessibility-toolkit-wx`。
- [ ] 設定 package-dir 指向 wx source。
- [ ] 設定 package discovery 只包含 `accessibility_toolkit_wx*`。
- [ ] 宣告 dependency：`accessibility-toolkit-core`。
- [ ] 宣告 dependency：`wxPython`。

建議驗證：

```bash
python -m build packages/accessibility-toolkit-core
python -m build packages/accessibility-toolkit-wx
```

## Phase 8：驗證安裝流程

- [ ] 建立乾淨 virtualenv。
- [ ] 安裝 core package。
- [ ] 驗證 `import accessibility_toolkit`。
- [ ] 驗證 `accessibility_toolkit.application`、`interop`、`adapters`、`runtime` 可 import。
- [ ] 安裝 wx package。
- [ ] 驗證 `import accessibility_toolkit_wx`。
- [ ] 驗證 app entrypoints 在已安裝 package 下可 import。

建議驗證：

```bash
python -m venv .venv-package-check
. .venv-package-check/bin/activate
pip install -e packages/accessibility-toolkit-core
pip install -e packages/accessibility-toolkit-wx
python -c "import accessibility_toolkit; import accessibility_toolkit_wx"
PYTHONPATH=src python -m apps.key_echo.main
```

備註：
- GUI app 的 runtime 驗證可能需要桌面環境。
- Windows 上要另外驗證 NVDA DLL 載入。

## Phase 9：移除 compatibility shims

執行前條件：

- [ ] `src/` 與 `tests/` 已無舊 namespace import。
- [ ] packages 可 build。
- [ ] unit tests 通過。
- [ ] integration tests 通過。

移除項目：

- [ ] 移除舊 `src/application/**` compatibility shims。
- [ ] 移除舊 `src/interop/**` compatibility shims。
- [ ] 移除舊 `src/adapters/**` compatibility shims。
- [ ] 移除舊 `src/bootstrap/**` compatibility shims。
- [ ] 移除舊 `src/apps/shared/**` compatibility shims。
- [ ] 移除舊 `src/ui/shared/**` compatibility shims。

搜尋檢查：

```bash
rg -n "from (application|interop|adapters|bootstrap|apps\.shared|ui\.shared)|import (application|interop|adapters|bootstrap|apps\.shared|ui\.shared)" src tests
```

## Phase 10：文件與最終驗收

- [ ] 更新 `README.md` 的安裝說明。
- [ ] 更新 `README.md` 的 app 執行方式。
- [ ] 更新 `AGENTS.md` 的專案結構說明。
- [ ] 更新 package build 指令。
- [ ] 補充 release 流程說明。
- [ ] 確認中文 migration 文件同步更新。

最終驗證：

```bash
PYTHONPATH=src pytest tests/unit tests/integration -v
python -m build packages/accessibility-toolkit-core
python -m build packages/accessibility-toolkit-wx
```

完成條件：

- [ ] 共用非 app 程式碼皆位於 `accessibility_toolkit`。
- [ ] wx UI 共用程式碼皆位於 `accessibility_toolkit_wx`。
- [ ] app code 不再 import 舊 shared 路徑。
- [ ] toolkit packages 不 import `apps.*` 或 app-specific `ui.*`。
- [ ] core package 不依賴 `wxPython`。
- [ ] wheels 與 sdists 可建立。
- [ ] 測試通過。
