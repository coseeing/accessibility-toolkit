# NVDA Remote Client

Python-based accessibility desktop app foundation built around a HID-first input model, shared speech/output services, mode-based event handling, a tray/tool app shell, and app-specific orchestration.

The repository is no longer just a standalone NVDA Remote client. It provides a common foundation that accessibility app layers can build on, with platform adapters normalizing native input, shared application services coordinating activation and output lifecycles, and app-specific orchestration living under `src/apps/`.

Current applications built on that foundation include:

- `access8graph`: GraphML-driven spoken navigation for accessibility-focused graph exploration
- `key_echo`: a keyboard echo demo app for validating input capture and speech behavior
- `nvda_remote`: an NVDA Remote relay client that forwards input and routes remote speech

## Current Status

The repository currently includes:

- Shared input activation, keyboard handling, and output scheduling services
- Shared protocol, message, and session models for remote interoperability
- App-specific services for `access8graph`, `key_echo`, and `nvda_remote`
- Windows adapter implementations for:
  - low-level keyboard hook setup
  - hotkey capture
  - clipboard access
  - vendored NVDA controller client DLL loading path
- macOS adapter implementations for keyboard capture, hotkey capture, and accessibility permission checks
- Reusable `wxPython` tool shell and speech settings UI
- Unit and integration tests for the core contracts and adapter behavior

What has been implemented in code has been manually validated on a real Windows machine. Real end-to-end relay compatibility, Windows UI behavior, keyboard hook behavior, clipboard updates, and NVDA speech output have been verified in that environment.

## Project Layout

```text
src/
  apps/          App-specific composition roots and orchestration
  application/   Shared input, output, keyboard, and speech services
  interop/       Shared protocol, message, speech, and key models
  adapters/      Platform-specific input/output implementations
  bootstrap/     Shared runtime/bootstrap wiring for desktop apps
  ui/            wxPython shells and app-specific frames
tests/
  unit/
  integration/
docs/
  superpowers/specs/
  superpowers/plans/
```

## Requirements

- Python 3.11+
- Windows or macOS for real runtime validation
- `wxPython` for the GUI
- NVDA installed and running locally on Windows if you want speech output through the vendored `x64/nvdaControllerClient.dll`

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

## Architecture

The runtime composition follows the same high-level shape across the current apps:

- platform adapters capture native keyboard and hotkey input and normalize it into shared models
- `application/` coordinates activation state, keyboard event routing, speech backends, and queued output
- `apps/*` define app-specific modes and behaviors on top of that shared pipeline
- `ui/*` hosts each app in a wxPython shell, with optional shared speech settings UI

At the app layer today:

- `access8graph` uses the shared hotkey/input lifecycle to enter a spoken graph navigation mode over GraphML data
- `key_echo` uses the same foundation to echo key events through selectable speech backends
- `nvda_remote` uses the same foundation plus relay/session logic to forward keyboard events and consume remote speech

## Run

Start `access8graph` with:

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
- use `WindowsHotkeyCapture`
- open a dedicated `wxPython` window with `Start` / `Stop` control and speech settings

The Access8Graph app is wired to:

- create a `SpeechService`
- create an `Access8GraphAppService`
- use shared input activation between `WindowsHotkeyCapture` / `MacOSHotkeyCapture` and full keyboard capture
- open a `wxPython` tool shell for selecting a `.graphml` file and entering navigation mode

## Package

Build the Access8Graph app as a macOS `.app` with the shared spec:

```bash
APP_TARGET=access8graph pyinstaller --clean --noconfirm packaging/macos_apps.spec
```

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

Build the Access8Graph app as a Windows executable with the shared spec:

```powershell
$env:APP_TARGET="access8graph"
pyinstaller --clean --noconfirm packaging/windows_apps.spec
```

On Windows `cmd.exe`:

```cmd
set APP_TARGET=access8graph
pyinstaller --clean --noconfirm packaging\windows_apps.spec
```

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

At the time of writing, the suite includes both unit and integration coverage for shared input/output behavior plus app-level coverage for `access8graph`, `key_echo`, and `nvda_remote`.

## Notes

- The relay transport includes TCP/TLS socket framing logic and buffered newline-delimited message parsing.
- Session state moves to `connected` only after `channel_joined` is received.
- Input capture and hotkey capture are activated through shared lifecycle logic so apps can switch cleanly between idle hotkey mode and active keyboard mode.
- The Windows keyboard hook, hotkey capture, clipboard backend, and NVDA controller DLL path are implemented behind adapters so shared application and interop layers stay free of `wx`, Win32, and DLL-specific imports.
- The vendored controller client DLL was taken from NVDA official controller client release zip and stored at `src/adapters/windows/vendor/nvda/x64/nvdaControllerClient.dll`.
- Remote `speak` payloads are deserialized into local speech command objects before routing, then carried through as full speech sequences to the active speech backend.
- The `pyttsx3` backend now schedules real breaks from remote `BreakCommand` items and applies rate, pitch, volume, and voice selection on a best-effort basis.
- The shared speech settings UI exposes speech backend, voice, rate, pitch, and volume controls through `SpeechService`.

## Related Docs

- [Design spec](docs/superpowers/specs/2026-05-31-nvda-remote-client-design.md)
- [Traditional Chinese design spec](docs/superpowers/specs/2026-05-31-nvda-remote-client-design_zh-TW.md)
- [Implementation plan](docs/superpowers/plans/2026-05-31-nvda-remote-client-implementation.md)
