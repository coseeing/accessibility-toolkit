# NVDA Remote Client

Standalone NVDA Remote client for Windows, implemented in Python.

This project is intended to connect to an existing NVDA Remote relay/server endpoint and control another machine that is already running NVDA Remote. The codebase is structured so protocol/session logic stays separate from Windows-specific input/output adapters, with the longer-term goal of making platform ports easier.

## Current Status

The repository currently includes:

- Relay protocol, JSON framing, and session state handling
- A modular application/controller layer
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
  remote_core/   Protocol, transport, session, routing, models
  application/   Controller, state, app-facing services
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

Start the GUI with:

```bash
PYTHONPATH=src python -m ui.main
```

The application is wired to:

- create a `RelayTransport`
- create a `ClientController`
- use `WindowsKeyboardCapture`
- use `WindowsClipboardService`
- attempt to load `src/adapters/windows/vendor/nvda/x64/nvdaControllerClient.dll` first, then fall back to `nvdaControllerClient64.dll` on the system path

## Package

Build a Windows executable with `PyInstaller`:

```bash
pyinstaller --name nvda-remote-client --windowed --onefile --paths src --add-binary "src/adapters/windows/vendor/nvda/x64/nvdaControllerClient.dll;adapters/windows/vendor/nvda/x64" --collect-submodules pyttsx3 src/ui/main.py
```

The packaged output will be written under:

```text
dist/
```

If you want a directory-style build instead of `--onefile`:

```bash
pyinstaller --name nvda-remote-client --windowed --paths src --add-binary "src/adapters/windows/vendor/nvda/x64/nvdaControllerClient.dll;adapters/windows/vendor/nvda/x64" --collect-submodules pyttsx3 src/ui/main.py
```

`pyttsx3` is imported dynamically at runtime, so the PyInstaller command includes `--collect-submodules pyttsx3` to ensure the packaged build can switch to the `pyttsx3` speech backend successfully.

## Test

Run the test suite with:

```bash
pytest tests/unit tests/integration -v
```

At the time of writing, the suite passes with 70 tests.

## Notes

- The relay transport now includes TCP/TLS socket framing logic and buffered newline-delimited message parsing.
- Session state moves to `connected` only after `channel_joined` is received.
- The Windows keyboard hook, clipboard backend, and NVDA controller DLL path are implemented behind adapters so `remote_core` stays free of `wx`, Win32, and DLL-specific imports.
- The vendored controller client DLL was taken from NVDA official controller client release zip and stored at `src/adapters/windows/vendor/nvda/x64/nvdaControllerClient.dll`.
- Remote `speak` payloads are deserialized into local speech command objects before routing, then carried through as full speech sequences to the active speech backend.
- The `pyttsx3` backend now schedules real breaks from remote `BreakCommand` items and applies rate, pitch, volume, and voice selection on a best-effort basis.
- The GUI exposes `pyttsx3` voice, rate, pitch, and volume controls through the main window.

## Related Docs

- [Design spec](docs/superpowers/specs/2026-05-31-nvda-remote-client-design.md)
- [Traditional Chinese design spec](docs/superpowers/specs/2026-05-31-nvda-remote-client-design_zh-TW.md)
- [Implementation plan](docs/superpowers/plans/2026-05-31-nvda-remote-client-implementation.md)
