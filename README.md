# accessibility-toolkit

`accessibility-toolkit` is a Python toolkit for building desktop accessibility applications. It organizes the common capabilities found in accessibility apps into a shared foundation. Its core areas are keyboard and hotkey capture, a keyboard event handling pipeline, speech and output scheduling, mode switching and interaction control, and application interfaces.

This repository currently includes three applications built on the toolkit:

- `access8graph`
  - GraphML-driven spoken MRT navigation
- `key_echo`
  - a demo app for validating how apps are composed and how interaction flows behave across input, handling, and output
- `nvda_remote`
  - NVDA Remote relay client for forwarding input and consuming remote speech

## Overview

Accessibility applications usually need input capture, event transformation, speech feedback, mode switching, and application interfaces. The goal of this project is to organize those recurring needs into a reusable toolkit so new applications can build on a shared foundation instead of reimplementing the same pieces inside each app.

The toolkit currently provides these 5 shared capabilities:

- keyboard and hotkey capture
- keyboard event handling pipeline
- speech and output scheduling
- mode switching and interaction control
- application interfaces

## What's Included

- Shared runtime components and services built around those 5 shared capabilities
- Shared tool shell and speech settings UI
- Windows adapters for keyboard hooks, hotkey capture, clipboard access, and NVDA Controller speech
- macOS adapters for keyboard capture, hotkey capture, and accessibility permission checks
- Reference apps for remote control, key echo, and graph navigation built on the toolkit

## Current Status

The shared toolkit architecture is implemented and already used by all three applications.

## Quick Start

Create a virtual environment, install dependencies, and then run one of the apps:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Run an app:

```bash
PYTHONPATH=src python -m apps.access8graph.main
PYTHONPATH=src python -m apps.key_echo.main
PYTHONPATH=src python -m apps.nvda_remote.main
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
$env:PYTHONPATH="src"
python -m apps.key_echo.main
python -m apps.access8graph.main
python -m apps.nvda_remote.main
```

## Installation

Requirements:

- Python 3.11+
- Windows or macOS
- NVDA installed and running if you want speech output through the NVDA controller DLL on Windows

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
  apps/          app-specific orchestration and entrypoints
  application/   shared input, output, keyboard, and speech services
  interop/       shared key, speech, protocol, and transport models
  adapters/      platform-specific implementations
  bootstrap/     shared runtime/bootstrap wiring
  ui/            wxPython shells and app-specific panels
tests/
  unit/
  integration/
```

## Documentation

- [spec.md](spec.md)
  - system architecture, toolkit boundaries, and design context
- [prd.md](prd.md)
  - product framing, target users, requirements, and success criteria
- `docs/superpowers/specs/`
  - historical design documents for major implementation phases
- `docs/superpowers/plans/`
  - implementation plans tied to those design phases
