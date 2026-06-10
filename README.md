# NVDA Remote Client

Standalone NVDA Remote client for Windows, implemented in Python.

This project is intended to connect to an existing NVDA Remote relay/server endpoint and control another machine that is already running NVDA Remote. The codebase is structured so protocol/session logic stays separate from Windows-specific input/output adapters, with the longer-term goal of making platform ports easier.

## Current Status

The repository currently includes:

- Relay protocol, JSON framing, and session state handling
- Shared application services for keyboard and speech coordination
- App-specific services for `nvda_remote` and `key_echo`
- Windows adapter implementations for:
  - low-level keyboard hook setup
  - clipboard access
  - vendored NVDA controller client DLL loading path
- A `wxPython` GUI shell
- Unit and integration tests for the core contracts and adapter behavior

What has been implemented in code has been manually validated on a real Windows machine. Real end-to-end relay compatibility, Windows UI behavior, keyboard hook behavior, clipboard updates, and NVDA speech output have been verified in that environment.

## Project Layout

```text
src/
  apps/          App-specific composition roots and services
  remote_core/   Protocol, transport, session, routing, models
  application/   Shared keyboard/speech services and state
  adapters/      Input/output abstractions and Windows implementations
  ui/            wxPython app shell
tests/
  unit/
  integration/
docs/
  superpowers/specs/
  superpowers/plans/
```

## Requirements

- Python 3.11+
- Windows for real runtime validation
- `wxPython` for the GUI
- NVDA installed and running locally if you want speech output through the vendored `x64/nvdaControllerClient.dll`

## Install

On macOS or Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

On Windows `cmd.exe`:

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
pip install -e .
```

## Run

Start the NVDA Remote GUI with:

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

Start the standalone key echo demo with:

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

The NVDA Remote app is wired to:

- create a `RelayTransport`
- create a `SpeechService`
- create a `NvdaRemoteAppService`
- use `WindowsKeyboardCapture`
- use `WindowsHotkeyCapture`
- use `WindowsClipboardService`
- load `src/adapters/windows/vendor/nvda/x64/nvdaControllerClient.dll`

The key echo demo is wired to:

- create a `SpeechService` with `pyttsx3` and `NVDA Controller` backend options
- create a `KeyEchoAppService`
- use `WindowsKeyboardCapture`
- open a dedicated `wxPython` window with `Start` / `Stop` control and speech settings

## Package

Build the key echo demo as a macOS `.app` with the shared spec:

```bash
APP_TARGET=key_echo pyinstaller --clean --noconfirm packaging/macos_apps.spec
```

Build the NVDA Remote GUI as a macOS `.app` with the shared spec:

```bash
APP_TARGET=nvda_remote pyinstaller --clean --noconfirm packaging/macos_apps.spec
```

Build both macOS `.app` bundles in one run with:

```bash
pyinstaller --clean --noconfirm packaging/macos_apps.spec
```

The macOS spec lives at `packaging/macos_apps.spec`. It collects `pyttsx3` submodules plus the lazily imported macOS input adapters required by the `.app` bundles.

Build the NVDA Remote GUI as a Windows executable with the shared spec:

```powershell
$env:APP_TARGET="nvda_remote"
pyinstaller --clean --noconfirm packaging/windows_apps.spec
```

On Windows `cmd.exe`:

```cmd
set APP_TARGET=nvda_remote
pyinstaller --clean --noconfirm packaging\windows_apps.spec
```

Build the key echo demo as a Windows executable with the shared spec:

```powershell
$env:APP_TARGET="key_echo"
pyinstaller --clean --noconfirm packaging/windows_apps.spec
```

On Windows `cmd.exe`:

```cmd
set APP_TARGET=key_echo
pyinstaller --clean --noconfirm packaging\windows_apps.spec
```

Build both Windows executables in one run with:

```powershell
Remove-Item Env:APP_TARGET -ErrorAction Ignore
pyinstaller --clean --noconfirm packaging/windows_apps.spec
```

On Windows `cmd.exe`:

```cmd
set APP_TARGET=
pyinstaller --clean --noconfirm packaging\windows_apps.spec
```

The packaged output will be written under:

```text
dist/
```

The Windows spec lives at `packaging/windows_apps.spec`. It keeps the vendored NVDA controller DLL, `pyttsx3` submodules, and the lazily imported Windows adapters in one place instead of repeating them on the command line.

`pyttsx3` and platform adapters are imported lazily at runtime, so the PyInstaller specs include explicit hidden imports for the platform adapters used by each packaged executable.

## Test

Run the test suite on macOS or Linux with:

```bash
pytest tests/unit tests/integration -v
```

On Windows PowerShell:

```powershell
pytest tests/unit tests/integration -v
```

On Windows `cmd.exe`:

```cmd
pytest tests\unit tests\integration -v
```

At the time of writing, the suite includes both unit and integration coverage for the shared keyboard service, shared speech service, NVDA Remote app service, and key echo app service.

## Notes

- The relay transport now includes TCP/TLS socket framing logic and buffered newline-delimited message parsing.
- Session state moves to `connected` only after `channel_joined` is received.
- The Windows keyboard hook, hotkey capture, clipboard backend, and NVDA controller DLL path are implemented behind adapters so `remote_core` stays free of `wx`, Win32, and DLL-specific imports.
- The vendored controller client DLL was taken from NVDA official controller client release zip and stored at `src/adapters/windows/vendor/nvda/x64/nvdaControllerClient.dll`.
- Remote `speak` payloads are deserialized into local speech command objects before routing, then carried through as full speech sequences to the active speech backend.
- The `pyttsx3` backend now schedules real breaks from remote `BreakCommand` items and applies rate, pitch, volume, and voice selection on a best-effort basis.
- The GUI exposes speech backend, voice, rate, pitch, and volume controls through the main window via `SpeechService`.

## Related Docs

- [Design spec](docs/superpowers/specs/2026-05-31-nvda-remote-client-design.md)
- [Traditional Chinese design spec](docs/superpowers/specs/2026-05-31-nvda-remote-client-design_zh-TW.md)
- [Implementation plan](docs/superpowers/plans/2026-05-31-nvda-remote-client-implementation.md)
