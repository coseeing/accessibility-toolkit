# accessibility-toolkit

`accessibility-toolkit` 是一套以 Python 開發的桌面無障礙應用工具套件。它提供一個共通基礎，涵蓋 HID-first 鍵盤輸入、mode-based 事件處理、語音／輸出服務，以及可重複使用的 wxPython 工具型應用殼層。

目前這個 repository 內含三個建立在 toolkit 之上的參考應用：

- `access8graph`
  - 以 GraphML 為基礎的捷運語音導覽工具
- `key_echo`
  - 用來驗證輸入與語音行為的鍵盤回饋示範程式
- `nvda_remote`
  - 將輸入轉送到遠端並接收遠端語音的 NVDA Remote relay client

## 專案概觀

這個專案最早從獨立的 NVDA Remote client 開始，之後因為多個無障礙應用需要共用相同的執行期能力，逐步演進成共享 toolkit：

- 鍵盤與快速鍵擷取
- idle / active mode 切換
- 語音後端管理
- 佇列化輸出行為
- 桌面工具型應用殼層與設定介面

這個 repository 的目標，是讓新的無障礙應用可以直接重用這些基礎設施，而不是在每個 app 內重新實作一次。

## 內含內容

- 共用的輸入啟用、鍵盤處理與輸出排程服務
- 供 remote 互通使用的共用協定、訊息與 session 模型
- 共用的 wxPython 工具殼層與語音設定介面
- Windows 平台的鍵盤 hook、快速鍵擷取、剪貼簿與 NVDA Controller 語音 adapter
- macOS 平台的鍵盤擷取、快速鍵擷取與輔助使用權限 adapter
- 用來驗證 toolkit 的 remote control、key echo 與圖形導覽參考 app
- 涵蓋共享層與 app 層行為的單元測試與整合測試

## 目前狀態

共享 toolkit 架構已實作完成，並且已被三個參考 app 實際使用。Windows 上的實際執行行為已手動驗證，包括 relay 相容性、鍵盤 hook 行為、剪貼簿同步與 NVDA 語音輸出。macOS 已有共享層與 app bootstrap 路徑，但目前實機驗證的完整度仍低於 Windows。

## 快速開始

建立虛擬環境、安裝相依套件，然後執行其中一個 app：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
PYTHONPATH=src python -m apps.access8graph.main
```

其他常用入口：

```bash
PYTHONPATH=src python -m apps.key_echo.main
PYTHONPATH=src python -m apps.nvda_remote.main
```

Windows PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
$env:PYTHONPATH="src"
python -m apps.access8graph.main
```

## 安裝

需求：

- Python 3.11+
- Windows 或 macOS，才能做實際執行驗證
- `wxPython` GUI
- 若要在 Windows 上使用 vendored controller DLL 的語音輸出，需安裝並啟動 NVDA

在 macOS 或 Linux 安裝：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

在 Windows PowerShell 安裝：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

在 Windows `cmd.exe` 安裝：

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
pip install -e .
```

## 執行

啟動 `access8graph`：

```bash
PYTHONPATH=src python -m apps.access8graph.main
```

Windows PowerShell：

```powershell
$env:PYTHONPATH="src"
python -m apps.access8graph.main
```

Windows `cmd.exe`：

```cmd
set PYTHONPATH=src
python -m apps.access8graph.main
```

啟動 `key_echo`：

```bash
PYTHONPATH=src python -m apps.key_echo.main
```

Windows PowerShell：

```powershell
$env:PYTHONPATH="src"
python -m apps.key_echo.main
```

Windows `cmd.exe`：

```cmd
set PYTHONPATH=src
python -m apps.key_echo.main
```

啟動 `nvda_remote`：

```bash
PYTHONPATH=src python -m apps.nvda_remote.main
```

Windows PowerShell：

```powershell
$env:PYTHONPATH="src"
python -m apps.nvda_remote.main
```

Windows `cmd.exe`：

```cmd
set PYTHONPATH=src
python -m apps.nvda_remote.main
```

## 建置

將 `access8graph` 建置為 macOS `.app`：

```bash
APP_TARGET=access8graph pyinstaller --clean --noconfirm packaging/macos_apps.spec
```

將 `key_echo` 建置為 macOS `.app`：

```bash
APP_TARGET=key_echo pyinstaller --clean --noconfirm packaging/macos_apps.spec
```

將 `nvda_remote` 建置為 macOS `.app`：

```bash
APP_TARGET=nvda_remote pyinstaller --clean --noconfirm packaging/macos_apps.spec
```

一次建置全部 macOS `.app`：

```bash
pyinstaller --clean --noconfirm packaging/macos_apps.spec
```

將 `access8graph` 建置為 Windows 可執行檔：

```powershell
$env:APP_TARGET="access8graph"
pyinstaller --clean --noconfirm packaging/windows_apps.spec
```

Windows `cmd.exe`：

```cmd
set APP_TARGET=access8graph
pyinstaller --clean --noconfirm packaging\windows_apps.spec
```

將 `key_echo` 建置為 Windows 可執行檔：

```powershell
$env:APP_TARGET="key_echo"
pyinstaller --clean --noconfirm packaging/windows_apps.spec
```

Windows `cmd.exe`：

```cmd
set APP_TARGET=key_echo
pyinstaller --clean --noconfirm packaging\windows_apps.spec
```

將 `nvda_remote` 建置為 Windows 可執行檔：

```powershell
$env:APP_TARGET="nvda_remote"
pyinstaller --clean --noconfirm packaging/windows_apps.spec
```

Windows `cmd.exe`：

```cmd
set APP_TARGET=nvda_remote
pyinstaller --clean --noconfirm packaging\windows_apps.spec
```

一次建置全部 Windows 可執行檔：

```powershell
Remove-Item Env:APP_TARGET -ErrorAction Ignore
pyinstaller --clean --noconfirm packaging/windows_apps.spec
```

共用的建置 spec 位於：

- `packaging/macos_apps.spec`
- `packaging/windows_apps.spec`

## 專案結構

```text
src/
  apps/          app 專屬 orchestration 與 entrypoint
  application/   共用輸入、輸出、鍵盤與語音服務
  interop/       共用 key、speech、protocol 與 transport 模型
  adapters/      平台專屬實作
  bootstrap/     共用 runtime / bootstrap wiring
  ui/            wxPython 殼層與 app 專屬 frame
tests/
  unit/
  integration/
docs/
  zh_TW/
  superpowers/specs/
  superpowers/plans/
```

## 文件

- [spec.md](../../spec.md)
  - 系統架構、toolkit 邊界與設計脈絡
- [prd.md](../../prd.md)
  - 產品定位、目標使用者、需求與成功指標
- `docs/superpowers/specs/`
  - 各主要實作階段的歷史設計文件
- `docs/superpowers/plans/`
  - 與這些設計階段對應的實作計畫
