# NVDA Remote Client

Standalone NVDA Remote client for Windows, with in-progress macOS keyboard capture support, implemented in Python.

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
- macOS adapter scaffolding for:
  - Quartz event-tap keyboard capture integration via `PyObjC` seams
  - `F11` hotkey capture/control toggling adapters
- A `wxPython` GUI shell
- Unit and integration tests for the core contracts and adapter behavior

What has been implemented in code has been manually validated on a real Windows machine. Real end-to-end relay compatibility, Windows UI behavior, keyboard hook behavior, clipboard updates, and NVDA speech output have been verified in that environment.

The current macOS scope is narrower. The macOS path is limited to global keyboard capture plus `F11` control toggling, and it is being built around Quartz event taps exposed through `PyObjC`. The adapter layer and runtime requirements are in place, but the full Quartz backend wiring is not complete yet. Clipboard integration and NVDA controller integration remain Windows-specific.

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
- Windows for full runtime validation
- macOS for Quartz keyboard capture runtime validation
- `wxPython` for the GUI
- NVDA installed and running locally if you want speech output through the vendored `x64/nvdaControllerClient.dll`
- On macOS, `PyObjC` provides the Quartz/ApplicationServices bridge used by keyboard capture
- On macOS, the app must be granted both `Accessibility` and `Input Monitoring` permissions for global keyboard capture and suppression to work

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

On Windows PowerShell, activate the virtual environment with:

```powershell
.venv\Scripts\Activate.ps1
```

## Run

Start the NVDA Remote GUI with:

```bash
PYTHONPATH=src python -m apps.nvda_remote.main
```

Start the standalone key echo demo with:

```bash
PYTHONPATH=src python -m apps.key_echo.main
```

The NVDA Remote app is wired to:

- create a `RelayTransport`
- create a `SpeechService`
- create a `NvdaRemoteAppService`
- use `WindowsKeyboardCapture` and `WindowsHotkeyCapture` on Windows
- use `MacOSKeyboardCapture` and `MacOSHotkeyCapture` on macOS
- use `WindowsClipboardService` on Windows
- use a safe unsupported clipboard fallback on non-Windows platforms until a native clipboard adapter exists
- load `src/adapters/windows/vendor/nvda/x64/nvdaControllerClient.dll`

On macOS, runtime validation should confirm:

- Quartz event taps can start through the `PyObjC` bridge
- The process has `Accessibility` and `Input Monitoring` permission
- Global keyboard capture works while the app is not focused
- `F11` toggles control mode and suppresses the local `F11` event

Current macOS limitation summary:

- Only keyboard capture and `F11` hotkey control toggling are in scope
- Clipboard behavior remains Windows-specific
- NVDA controller DLL loading and speech integration remain Windows-specific

The key echo demo is wired to:

- create a `SpeechService` with `pyttsx3` and `NVDA Controller` backend options
- create a `KeyEchoAppService`
- use `WindowsKeyboardCapture`
- open a dedicated `wxPython` window with `Start` / `Stop` control and speech settings

## Package

Build the NVDA Remote GUI as a Windows executable with `PyInstaller`:

```bash
pyinstaller --name nvda-remote-client --windowed --onefile --paths src --add-binary "src/adapters/windows/vendor/nvda/x64/nvdaControllerClient.dll;adapters/windows/vendor/nvda/x64" --collect-submodules pyttsx3 src/apps/nvda_remote/main.py
```

Build the key echo demo as a Windows executable with:

```bash
pyinstaller --name key-echo-demo --windowed --onefile --paths src --add-binary "src/adapters/windows/vendor/nvda/x64/nvdaControllerClient.dll;adapters/windows/vendor/nvda/x64" --collect-submodules pyttsx3 src/apps/key_echo/main.py
```

The packaged output will be written under:

```text
dist/
```

If you want a directory-style build instead of `--onefile`:

```bash
pyinstaller --name nvda-remote-client --windowed --paths src --add-binary "src/adapters/windows/vendor/nvda/x64/nvdaControllerClient.dll;adapters/windows/vendor/nvda/x64" --collect-submodules pyttsx3 src/apps/nvda_remote/main.py
```

`pyttsx3` is imported dynamically at runtime, so the PyInstaller command includes `--collect-submodules pyttsx3` to ensure the packaged build can switch to the `pyttsx3` speech backend successfully.

## Test

Run the test suite with:

```bash
pytest tests/unit tests/integration -v
```

At the time of writing, the suite includes both unit and integration coverage for the shared keyboard service, shared speech service, NVDA Remote app service, and key echo app service.

## Notes

- The relay transport now includes TCP/TLS socket framing logic and buffered newline-delimited message parsing.
- Session state moves to `connected` only after `channel_joined` is received.
- The Windows keyboard hook, macOS adapter/event-tap seam, clipboard backend, and NVDA controller DLL path are implemented behind adapters so `remote_core` stays free of `wx`, Win32, Quartz, and DLL-specific imports.
- The vendored controller client DLL was taken from NVDA official controller client release zip and stored at `src/adapters/windows/vendor/nvda/x64/nvdaControllerClient.dll`.
- Remote `speak` payloads are deserialized into local speech command objects before routing, then carried through as full speech sequences to the active speech backend.
- The `pyttsx3` backend now schedules real breaks from remote `BreakCommand` items and applies rate, pitch, volume, and voice selection on a best-effort basis.
- The GUI exposes speech backend, voice, rate, pitch, and volume controls through the main window via `SpeechService`.

## Related Docs

- [Design spec](docs/superpowers/specs/2026-05-31-nvda-remote-client-design.md)
- [Traditional Chinese design spec](docs/superpowers/specs/2026-05-31-nvda-remote-client-design_zh-TW.md)
- [Implementation plan](docs/superpowers/plans/2026-05-31-nvda-remote-client-implementation.md)
