# accessibility-toolkit

`accessibility-toolkit` 是一套以 Python 開發的桌面無障礙應用工具套件。它將無障礙應用常見的共通功能整理為可共享的基礎能力，核心包括鍵盤與快速鍵擷取、鍵盤事件處理管線、語音與輸出排程、模式切換與互動控制，以及應用程式介面。

目前這個專案內含三個建立在 toolkit 之上的應用：

- `access8graph`
  - 以 GraphML 為基礎的捷運語音導覽工具
- `key_echo`
  - 用來驗證各應用的組裝方式與互動行為（輸入、處理、輸出）的示範程式
- `nvda_remote`
  - 將鍵盤輸入轉送到遠端並接收遠端語音輸出的 NVDA Remote relay client

## 專案概覽

無障礙應用通常都需要處理輸入擷取、事件轉換、語音回饋、模式切換，以及應用程式介面。這個專案的目標，是把這些常見需求整理成可重用的 toolkit，讓新的應用可以直接建立在共享基礎上，而不是在每個 app 中各自重做一次。

目前 toolkit 包括以下 5 項共用功能：

- 鍵盤與快速鍵擷取
- 鍵盤事件處理管線
- 語音與輸出排程
- 模式切換與互動控制
- 應用程式介面

## 內含提供

- 以這 5 項共用功能為基礎的共享執行期元件與服務
- 共用的工具殼層與語音設定介面
- Windows 平台的鍵盤擷取、快速鍵擷取、剪貼簿與 NVDA Controller 語音 adapter
- macOS 平台的鍵盤擷取、快速鍵擷取與輔助使用權限 adapter
- 建立在 toolkit 之上的 remote control、key echo 與圖形導覽參考應用

共享 toolkit 架構已實作完成，並且已被三個應用實際使用。

## 快速開始

建立虛擬環境、安裝相依套件，然後執行其中一個 app：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

執行應用：

```bash
PYTHONPATH=src python -m apps.access8graph.main
PYTHONPATH=src python -m apps.key_echo.main
PYTHONPATH=src python -m apps.nvda_remote.main
```

Windows PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
$env:PYTHONPATH="src"
python -m apps.key_echo.main
python -m apps.access8graph.main
python -m apps.nvda_remote.main
```

## 安裝

需求：

- Python 3.11+
- Windows 或 macOS
- 若要在 Windows 上使用 NVDA controller DLL 的語音輸出，需安裝並啟動 NVDA

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

啟動 `access8graph` 並開啟檔案 logging：

```bash
ACCESSIBILITY_TOOLKIT_LOGGING=1 PYTHONPATH=src python -m apps.access8graph.main
```

Windows PowerShell：

```powershell
$env:PYTHONPATH="src"
python -m apps.access8graph.main
```

在 Windows PowerShell 開啟檔案 logging：

```powershell
$env:ACCESSIBILITY_TOOLKIT_LOGGING="1"
$env:PYTHONPATH="src"
python -m apps.access8graph.main
```

Windows `cmd.exe`：

```cmd
set PYTHONPATH=src
python -m apps.access8graph.main
```

在 Windows `cmd.exe` 開啟檔案 logging：

```cmd
set ACCESSIBILITY_TOOLKIT_LOGGING=1
set PYTHONPATH=src
python -m apps.access8graph.main
```

啟動 `key_echo`：

```bash
PYTHONPATH=src python -m apps.key_echo.main
```

啟動 `key_echo` 並開啟檔案 logging：

```bash
ACCESSIBILITY_TOOLKIT_LOGGING=1 PYTHONPATH=src python -m apps.key_echo.main
```

Windows PowerShell：

```powershell
$env:PYTHONPATH="src"
python -m apps.key_echo.main
```

在 Windows PowerShell 開啟檔案 logging：

```powershell
$env:ACCESSIBILITY_TOOLKIT_LOGGING="1"
$env:PYTHONPATH="src"
python -m apps.key_echo.main
```

Windows `cmd.exe`：

```cmd
set PYTHONPATH=src
python -m apps.key_echo.main
```

在 Windows `cmd.exe` 開啟檔案 logging：

```cmd
set ACCESSIBILITY_TOOLKIT_LOGGING=1
set PYTHONPATH=src
python -m apps.key_echo.main
```

啟動 `nvda_remote`：

```bash
PYTHONPATH=src python -m apps.nvda_remote.main
```

啟動 `nvda_remote` 並開啟檔案 logging：

```bash
ACCESSIBILITY_TOOLKIT_LOGGING=1 PYTHONPATH=src python -m apps.nvda_remote.main
```

Windows PowerShell：

```powershell
$env:PYTHONPATH="src"
python -m apps.nvda_remote.main
```

在 Windows PowerShell 開啟檔案 logging：

```powershell
$env:ACCESSIBILITY_TOOLKIT_LOGGING="1"
$env:PYTHONPATH="src"
python -m apps.nvda_remote.main
```

Windows `cmd.exe`：

```cmd
set PYTHONPATH=src
python -m apps.nvda_remote.main
```

在 Windows `cmd.exe` 開啟檔案 logging：

```cmd
set ACCESSIBILITY_TOOLKIT_LOGGING=1
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

## macOS App 安裝

下載並解壓縮 `.zip` 後，macOS 可能因為隔離機制而封鎖 app 執行。在啟動前，請執行以下指令，將路徑替換為實際放置 app 的位置：

```bash
xattr -dr com.apple.quarantine /path/to/access8graph.app
```

## 專案結構

toolkit 將共用功能整理為 `accessibility_toolkit` 下的 7 個功能導向套件：

```text
src/
  accessibility_toolkit/
    input/         鍵盤輸入、HID、capture、管線
    output/        輸出排程與佇列服務
      speech/      語音序列、backend 與語音模型
    scheduling/    領域中立的排程器
    interaction/   模式生命週期與啟用控制
    events/        跨模組生命週期事件
    remote/        relay 協定與 session
    runtime/       app 組裝、平台解析、bootstrap wiring
  apps/            app 專屬 orchestration 與 entrypoint
  ui/              wxPython 殼層與 app 專屬面板
tests/
  unit/
  integration/
```

相依方向由下往上：`scheduling` 與 `events` 是基礎層，`input` 與 `interaction` 使用 `events`，`remote` 使用穩定的 output/speech wire 模型，`runtime` 負責 app 組裝。

```python
from accessibility_toolkit.input import KeyEvent, KeyboardInputService
from accessibility_toolkit.output import QueuedService
from accessibility_toolkit.output.speech import SpeechSequence, SpeechService
from accessibility_toolkit.scheduling import Scheduler
from accessibility_toolkit.interaction import ModeManager
from accessibility_toolkit.remote import RemoteSession
```

## 文件

- [spec.md](spec.md)
  - 系統架構、toolkit 邊界與設計脈絡
- [prd.md](prd.md)
  - 產品定位、目標使用者、需求與成功指標
- `docs/superpowers/specs/`
  - 各主要實作階段的歷史設計文件
- `docs/superpowers/plans/`
  - 與這些設計階段對應的實作計畫
