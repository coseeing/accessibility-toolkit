# accessibility-toolkit

`accessibility-toolkit` is a Python toolkit for building desktop accessibility applications. It provides a shared foundation for HID-first keyboard input, mode-based event handling, speech/output services, and reusable wxPython tool-app shell behavior.

This repository currently includes three reference applications built on that toolkit:

- `access8graph`
  - GraphML-driven spoken MRT navigation
- `key_echo`
  - keyboard echo demo for validating input and speech behavior
- `nvda_remote`
  - NVDA Remote relay client for forwarding input and consuming remote speech

## Overview

The project started from a standalone NVDA Remote client and evolved into a shared toolkit once multiple accessibility apps needed the same runtime capabilities:

- keyboard and hotkey capture
- idle / active mode switching
- speech backend management
- queued output behavior
- desktop tool shell and settings UI

The goal of the repository is to let new accessibility apps reuse this infrastructure instead of rebuilding it inside each app.

## What's Included

- Shared input activation, keyboard handling, and output scheduling services
- Shared protocol, message, and session models for remote interoperability
- Shared wxPython tool shell and speech settings UI
- Windows adapters for keyboard hooks, hotkey capture, clipboard access, and NVDA Controller speech
- macOS adapters for keyboard capture, hotkey capture, and accessibility permission checks
- Reference apps for remote control, key echo, and graph navigation
- Unit and integration tests covering both shared layers and app-level behavior

## Current Status

The shared toolkit architecture is implemented and in active use by all three reference apps. Real runtime behavior has been manually validated on Windows, including relay compatibility, keyboard hook behavior, clipboard updates, and NVDA speech output. macOS support exists in the shared layers and app bootstrap path, but runtime validation is still narrower than Windows.

## Quick Start

Create a virtual environment, install dependencies, and run one of the apps:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
PYTHONPATH=src python -m apps.access8graph.main
```

Other useful entrypoints:

```bash
PYTHONPATH=src python -m apps.key_echo.main
PYTHONPATH=src python -m apps.nvda_remote.main
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
$env:PYTHONPATH="src"
python -m apps.access8graph.main
```

## Installation

Requirements:

- Python 3.11+
- Windows or macOS for real runtime validation
- `wxPython` for the GUI
- NVDA installed and running locally on Windows if you want speech output through the vendored controller DLL

Install on macOS or Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Install on Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

Install on Windows `cmd.exe`:

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
pip install -e .
```

## Run

Start `access8graph`:

```bash
PYTHONPATH=src python -m apps.access8graph.main
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH="src"
python -m apps.access8graph.main
```

On Windows `cmd.exe`:

```cmd
set PYTHONPATH=src
python -m apps.access8graph.main
```

Start `key_echo`:

```bash
PYTHONPATH=src python -m apps.key_echo.main
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH="src"
python -m apps.key_echo.main
```

On Windows `cmd.exe`:

```cmd
set PYTHONPATH=src
python -m apps.key_echo.main
```

Start `nvda_remote`:

```bash
PYTHONPATH=src python -m apps.nvda_remote.main
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH="src"
python -m apps.nvda_remote.main
```

On Windows `cmd.exe`:

```cmd
set PYTHONPATH=src
python -m apps.nvda_remote.main
```

## Build

Build `access8graph` as a macOS `.app`:

```bash
APP_TARGET=access8graph pyinstaller --clean --noconfirm packaging/macos_apps.spec
```

Build `key_echo` as a macOS `.app`:

```bash
APP_TARGET=key_echo pyinstaller --clean --noconfirm packaging/macos_apps.spec
```

Build `nvda_remote` as a macOS `.app`:

```bash
APP_TARGET=nvda_remote pyinstaller --clean --noconfirm packaging/macos_apps.spec
```

Build all macOS `.app` bundles:

```bash
pyinstaller --clean --noconfirm packaging/macos_apps.spec
```

Build `access8graph` as a Windows executable:

```powershell
$env:APP_TARGET="access8graph"
pyinstaller --clean --noconfirm packaging/windows_apps.spec
```

On Windows `cmd.exe`:

```cmd
set APP_TARGET=access8graph
pyinstaller --clean --noconfirm packaging\windows_apps.spec
```

Build `key_echo` as a Windows executable:

```powershell
$env:APP_TARGET="key_echo"
pyinstaller --clean --noconfirm packaging/windows_apps.spec
```

On Windows `cmd.exe`:

```cmd
set APP_TARGET=key_echo
pyinstaller --clean --noconfirm packaging\windows_apps.spec
```

Build `nvda_remote` as a Windows executable:

```powershell
$env:APP_TARGET="nvda_remote"
pyinstaller --clean --noconfirm packaging/windows_apps.spec
```

On Windows `cmd.exe`:

```cmd
set APP_TARGET=nvda_remote
pyinstaller --clean --noconfirm packaging\windows_apps.spec
```

Build all Windows executables:

```powershell
Remove-Item Env:APP_TARGET -ErrorAction Ignore
pyinstaller --clean --noconfirm packaging/windows_apps.spec
```

The shared build specs live at:

- `packaging/macos_apps.spec`
- `packaging/windows_apps.spec`

## Project Layout

```text
src/
  apps/          App-specific orchestration and entrypoints
  application/   Shared input, output, keyboard, and speech services
  interop/       Shared key, speech, protocol, and transport models
  adapters/      Platform-specific implementations
  bootstrap/     Shared runtime/bootstrap wiring
  ui/            wxPython shells and app-specific frames
tests/
  unit/
  integration/
docs/
  zh_TW/
  superpowers/specs/
  superpowers/plans/
```

## Documentation

- [spec.md](spec.md)
  - system architecture, toolkit boundaries, and design context
- [prd.md](prd.md)
  - product framing, target users, requirements, and success criteria
- [docs/zh_TW/README.md](docs/zh_TW/README.md)
  - Traditional Chinese overview and onboarding guide
- [docs/zh_TW/spec.md](docs/zh_TW/spec.md)
  - Traditional Chinese architecture and system context
- [docs/zh_TW/prd.md](docs/zh_TW/prd.md)
  - Traditional Chinese product requirements document
- `docs/superpowers/specs/`
  - historical design documents for major implementation phases
- `docs/superpowers/plans/`
  - implementation plans tied to those design phases
