# Toolkit 套件遷移計畫

## 目標

將這個儲存庫重整為可獨立發佈的 Python 套件，讓共用的無障礙功能成為可安裝、可發布的 package，而應用程式專屬的程式碼則留在各自的 app 模組或獨立 repository 中。

這個目標不只是把 `apps/` 內的共用程式碼搬出去，而是要建立清楚的套件邊界、穩定的相依方向，以及能支援未來無障礙應用程式的可發布套件結構。

## 範圍

本計畫涵蓋：

- 共用的 runtime、domain、protocol 與平台整合程式碼
- 以 `wxPython` 為基礎的可選桌面 UI 支援程式碼
- 將 app 專屬功能與可重用的 toolkit 程式碼分離
- 能獨立發佈的套件打包與 release 結構

本計畫不包含：

- 重寫 app 行為
- 變更 `nvda_remote` 的 protocol 行為
- 立即將 `access8graph`、`key_echo` 或 `nvda_remote` 拆成獨立 repository

## 目前狀態

這個 repository 已經有不錯的架構切分，但 package 邊界尚未對齊可發佈的 artifact：

- `src/application`
  - 共用的 application 服務與協調邏輯
- `src/interop`
  - 共用的模型與 protocol contract
- `src/adapters`
  - 平台特定與輸入/輸出整合
- `src/bootstrap`
  - runtime 組裝輔助
- `src/apps/shared`
  - app 層共用輔助，目前位置不適合直接拿來發佈
- `src/ui/shared`
  - 可重用的 `wxPython` 桌面 shell 元件
- `src/apps/*`
  - app 專屬行為
- `src/ui/*`
  - app 專屬 UI entrypoint 與 frame

目前主要問題是「shared」程式碼跨越了多個架構層級：

- 核心 toolkit 邏輯
- runtime/bootstrap 輔助
- app support 輔助
- 可選的桌面 UI 輔助

這些都需要成為彼此獨立、可發佈的 surface。

## 目標套件結構

### 套件 1：`accessibility-toolkit-core`

用途：
- 發佈可重用、非 UI、跨應用程式的 toolkit 基礎

內容：
- `application`
- `interop`
- `adapters`
- `bootstrap`，或改名為 `runtime`

建議 namespace：

```text
src/accessibility_toolkit/
    application/
    interop/
    adapters/
    runtime/
```

備註：
- `bootstrap` 在新的 package namespace 底下應該依一致性改名為 `runtime` 或保留 `bootstrap`。
- 這個套件不應包含任何 app 專屬行為。
- 這個套件仍可包含平台 adapters，但要透過 optional dependency 與條件式 import 處理。

### 套件 2：`accessibility-toolkit-wx`

用途：
- 發佈供 toolkit 型 app 使用的可選 `wxPython` 桌面 shell 輔助功能

內容：
- 來自 `ui/shared` 的可重用程式碼
- 任何真正可跨 app 重用的 UI-facing controller/facade

建議 namespace：

```text
src/accessibility_toolkit_wx/
    shell/
    speech/
    tray/
```

建議遷移到這裡的模組：
- `ui/shared/panel_controller.py`
- `ui/shared/tool_app_shell.py`
- `ui/shared/speech_controls.py`
- `ui/shared/speech_settings_frame.py`
- `ui/shared/tray_icon.py`

備註：
- 這個套件必須依賴 `accessibility-toolkit-core`。
- `wxPython` 應該成為這個套件的明確相依，而不是 core 套件的相依，除非 core 真的仍然需要它。

### App 套件或 App 模組

用途：
- 將應用程式專屬行為與 toolkit 隔離

內容：
- `apps/nvda_remote`
- `apps/key_echo`
- `apps/access8graph`
- `ui/nvda_remote`
- `ui/echo`
- `ui/access8graph`

未來可能的套件化：
- `accessibility-toolkit-app-key-echo`
- `accessibility-toolkit-app-nvda-remote`
- `accessibility-toolkit-app-access8graph`

在第一階段遷移中，這些可以先保留在同一個 repository，並透過已發佈的 toolkit 套件來使用。

## 模組對照

### 移入 `accessibility-toolkit-core`

目前：
- `src/application/**`
- `src/interop/**`
- `src/adapters/**`
- `src/bootstrap/**`

目標：
- `src/accessibility_toolkit/application/**`
- `src/accessibility_toolkit/interop/**`
- `src/accessibility_toolkit/adapters/**`
- `src/accessibility_toolkit/runtime/**`

### 移入 `accessibility-toolkit-wx`

目前：
- `src/ui/shared/**`

目標：
- `src/accessibility_toolkit_wx/**`

### 重新安置目前位於 `apps/shared` 的支援模組

這些模組不應該繼續留在 `apps` 下。

#### `apps/shared/mode_manager.py`

建議：
- 搬到 `accessibility_toolkit/application_support/mode_manager.py`

原因：
- 可重用的互動支援邏輯
- 不綁定單一 app
- 也不是 UI 專屬

#### `apps/shared/speech_runtime_settings.py`

建議：
- 搬到 `accessibility_toolkit/runtime/speech_settings.py`
  或
- 搬到 `accessibility_toolkit/application_support/speech_runtime_settings.py`

原因：
- 這是協調 config persistence 與 runtime speech service 的整合輔助
- 可重用，但不屬於 domain core

#### `apps/shared/speech_settings_facade.py`

建議：
- 搬到 `accessibility_toolkit/application_support/speech_settings_facade.py`
  或如果它主要仍是 UI-facing，則搬到 `accessibility_toolkit_wx`

原因：
- 這是 presentation layer 的 controller/facade
- 可跨 app 使用，但不屬於低階 toolkit primitive

## 相依規則

遷移應該強制下列相依方向：

1. `accessibility-toolkit-core`
   - 不得 import 任何 app module
   - 不應依賴 `wxPython`

2. `accessibility-toolkit-wx`
   - 可依賴 `accessibility-toolkit-core`
   - 不得依賴特定 app

3. app modules/packages
   - 可依賴 `accessibility-toolkit-core`
   - 可依賴 `accessibility-toolkit-wx`
   - 不得被 toolkit packages import

4. platform-specific adapters
   - 保留在 toolkit packages 內
   - 應維持 lazy import 與 optional dependency 行為

## 打包策略

## Phase 0 的打包目標

保留單一 repository，但產出至少兩個可發佈套件：

- `accessibility-toolkit-core`
- `accessibility-toolkit-wx`

這可以透過以下方式實作：

- monorepo 搭配多個 `pyproject.toml` package root
- 或單一頂層 build system 搭配 subpackage build 設定

建議作法：
- 採用 monorepo 佈局，將獨立 package 目錄放在 `packages/` 底下

建議結構：

```text
packages/
    accessibility-toolkit-core/
        pyproject.toml
        src/accessibility_toolkit/...
    accessibility-toolkit-wx/
        pyproject.toml
        src/accessibility_toolkit_wx/...
src/apps/...
src/ui/...
tests/...
```

原因：
- 套件責任會更清楚
- 未來可再分開版本管理
- app 程式碼可以逐步遷移，不必立刻拆 repository

## 建議的遷移階段

### Phase 1：先定義套件邊界，不改行為

工作項目：
- 建立 `docs/toolkit-package-migration-plan.md`
- 確認 package 名稱與 namespace
- 決定 `bootstrap` 要改成 `runtime` 還是保留 `bootstrap`
- 決定 `speech_settings_facade` 應該放在 core support 還是 `wx` 套件

交付成果：
- 已核准的套件對照表與相依規則

### Phase 2：先在原地引入新的 namespace

工作項目：
- 建立新的 package root：
  - `src/accessibility_toolkit/`
  - `src/accessibility_toolkit_wx/`
- 將共用模組搬移：
  - `application` -> `accessibility_toolkit/application`
  - `interop` -> `accessibility_toolkit/interop`
  - `adapters` -> `accessibility_toolkit/adapters`
  - `bootstrap` -> `accessibility_toolkit/runtime`
- 將 `apps/shared` 模組搬到：
  - `accessibility_toolkit/application_support`
  - 或 `accessibility_toolkit_wx`
- 將 `ui/shared` 搬到 `accessibility_toolkit_wx`

限制條件：
- 搬移時不要改變行為
- 逐步更新 imports
- 每個子步驟後都要維持測試綠燈

交付成果：
- repository 可以編譯，測試在新 namespace 下通過

### Phase 3：加入相容性 shim

工作項目：
- 在需要的舊路徑下保留暫時性的相容模組
- 過渡期間由舊模組 re-export 新模組

範例：
- 舊的 `application` package 改為 import `accessibility_toolkit.application`
- 舊的 `ui.shared` 改為 import `accessibility_toolkit_wx`

原因：
- 降低遷移影響範圍
- 讓 app 程式碼可以逐步搬移
- 讓 review 與 rollback 更容易

交付成果：
- 舊 import 在過渡期間仍可正常運作

### Phase 4：更新 app entrypoint 與 app 內部程式碼

工作項目：
- 更新所有 app module，改從新 package namespace import
- 移除對舊 shared 位置的直接 import

主要受影響檔案：
- `src/apps/nvda_remote/main.py`
- `src/apps/key_echo/main.py`
- `src/apps/access8graph/main.py`
- 任何 import `apps.shared.mode_manager` 的 service
- import `ui.shared.*` 的 UI app entrypoint

交付成果：
- app 只依賴 toolkit package namespace，不再依賴舊路徑

### Phase 5：拆分 packaging metadata

工作項目：
- 為 `accessibility-toolkit-core` 建立 `pyproject.toml`
- 為 `accessibility-toolkit-wx` 建立 `pyproject.toml`
- 將 NVDA DLL 的 package data 宣告移到 core 套件
- 針對需要的地方定義 optional dependency

建議的相依拆分：

對於 `accessibility-toolkit-core`：
- 只保留基礎依賴
- macOS 依賴採 platform extras
- 若有需要，可加入可選 speech extras

對於 `accessibility-toolkit-wx`：
- 依賴 `accessibility-toolkit-core`
- 依賴 `wxPython`

交付成果：
- 兩個套件都可以獨立 build wheel 與 sdist

### Phase 6：測試套件安裝流程

工作項目：
- 單獨安裝 `accessibility-toolkit-core` 並驗證可 import
- 安裝 `accessibility-toolkit-core` 加 `accessibility-toolkit-wx`
- 使用已安裝的套件執行 app entrypoint，而不是依賴 repo 相對路徑
- 驗證 Windows DLL 的打包路徑

驗證方式：
- `pip install -e packages/accessibility-toolkit-core`
- `pip install -e packages/accessibility-toolkit-wx`
- 執行有針對性的 unit tests
- 執行完整 test suite

交付成果：
- 套件安裝與 runtime 行為都已驗證

### Phase 7：移除舊的相容層

工作項目：
- 等所有 imports 更新完後，移除舊的頂層 package alias
- 刪除失效的相容檔案
- 更新 README 與開發文件，改用正式發佈的 package import

交付成果：
- 最終 package 結構乾淨，沒有重複的 import 路徑

## 詳細技術決策

### 1. 在單一 vendor namespace 下重新命名頂層 package

目前像 `application`、`interop`、`adapters` 這種頂層模組名稱對發佈來說太過通用。

建議：
- 將它們統一收斂到 `accessibility_toolkit` 底下

原因：
- 避免 import 名稱衝突
- 讓公開 API 更清楚
- 為未來擴充建立穩定 namespace

### 2. 將支援層與 core primitives 分開

不是所有可重用程式碼都應該放在同一個 package layer。

建議拆分：
- core primitives 與 services：
  - `accessibility_toolkit.application`
  - `accessibility_toolkit.interop`
  - `accessibility_toolkit.adapters`
- runtime 與組裝：
  - `accessibility_toolkit.runtime`
- app support：
  - `accessibility_toolkit.application_support`
- 可選桌面 UI：
  - `accessibility_toolkit_wx`

### 3. 避免 toolkit package import app 程式碼

toolkit packages 不得 import：
- `apps.nvda_remote`
- `apps.key_echo`
- `apps.access8graph`
- app 專屬 UI module

任何需要 app 專屬 callback 的地方，應該改用參數或 port 傳入。

### 4. 重新檢視目前的相依範圍

目前根 package 的相依包含：
- `wxPython`
- `pyinstaller`
- `pyttsx3`
- macOS 的 `pyobjc` packages

對於可發佈套件：
- `pyinstaller` 不應該成為 toolkit package 的 runtime 依賴
- `wxPython` 應該移到可選的 UI 套件
- 平台依賴應該設計成 optional 或平台限定

建議方向：

`accessibility-toolkit-core`
- `pyttsx3`
- 若 bundled adapters 需要，則保留帶條件標記的 macOS `pyobjc`

`accessibility-toolkit-wx`
- `wxPython`
- 依賴 `accessibility-toolkit-core`

App packaging 或 build tooling
- `pyinstaller`

## 風險

### import 變更量大

大規模 rename 會碰到很多檔案與測試。

緩解方式：
- 分階段搬移
- 暫時使用相容 shim
- 每個階段同步更新測試

### 分層界線外洩

目前有些模組同時混合了 runtime 協調與 UI 導向行為。

緩解方式：
- 搬移前先分類每個模組
- 不要強行把模糊模組塞進 core

### Windows 打包回歸

搬移 `adapters.windows` 後，NVDA DLL 的打包路徑必須保持正確。

緩解方式：
- 測試 wheel 內容
- 在 Windows 上測試 runtime 載入
- 將 package data 宣告維持在新的 core package 附近

### optional dependency 失效

如果套件邊界切錯，平台特定 import 可能會失敗。

緩解方式：
- 在 adapters 保持 lazy import pattern
- 在非 Windows 與非 macOS 環境驗證 import 行為

## 初始工作拆解

建議的第一輪實作順序如下：

1. 核准這份遷移計畫
2. 確認下列命名：
   - `accessibility_toolkit.runtime` 與 `accessibility_toolkit.bootstrap` 之間的選擇
   - `accessibility_toolkit.application_support`
   - `accessibility_toolkit_wx`
3. 建立新的 package 目錄並搬移 core 模組
4. 加入相容性 shim
5. 遷移 `apps/shared`
6. 遷移 `ui/shared`
7. 更新 app imports
8. 拆分 packaging metadata
9. 驗證安裝與測試流程
10. 移除相容性 shim

## 建議先確認的決策

在開始搬移程式碼之前，應先確認下列事項：

1. Core package 名稱
   - 建議：`accessibility-toolkit-core`

2. Core Python namespace
   - 建議：`accessibility_toolkit`

3. UI package 名稱
   - 建議：`accessibility-toolkit-wx`

4. UI Python namespace
   - 建議：`accessibility_toolkit_wx`

5. Runtime package 命名
   - 建議內部模組名稱：`runtime`

6. Support layer 的位置
   - 建議：`accessibility_toolkit.application_support`

## 成功標準

當下列條件成立時，遷移就算完成：

- 共用的非 app 程式碼可以從可發佈的 toolkit namespace 匯入
- toolkit packages 不會 import app modules
- 可選的 `wxPython` UI 輔助功能已與 core 套件隔離
- app 程式碼改為依賴 toolkit packages，而不是舊的 shared 路徑
- 能針對共用套件建立 wheels 與 sdists
- 測試在新的 package 結構下通過
