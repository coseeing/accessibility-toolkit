# Repository Guidelines

## Project Structure & Module Organization

Source code lives under `src/` using a `src` layout. Key areas:
- `src/apps/`: application entrypoints and app-specific services for `nvda_remote` and `key_echo`
- `src/application/`: shared business logic for keyboard, speech, and output coordination
- `src/interop/`: protocol, message, and session models used across apps
- `src/adapters/`: platform-specific input/output implementations, including Windows and macOS code
- `src/ui/`: wxPython UI shell and shared UI helpers
- `tests/`: unit tests in `tests/unit/` and integration coverage in `tests/integration/`

## Build, Test, and Development Commands

- `python -m venv .venv` and activate it before local work.
- `pip install -e .` installs the package and its runtime dependencies.
- `PYTHONPATH=src python -m apps.nvda_remote.main` runs the main NVDA Remote client.
- `PYTHONPATH=src python -m apps.key_echo.main` runs the key echo demo.
- `pytest tests/unit tests/integration -v` runs the full test suite.
- `pyinstaller ... src/apps/nvda_remote/main.py` builds the Windows executable; use the command shown in `README.md` when packaging.

## Coding Style & Naming Conventions

Follow standard Python style with 4-space indentation, descriptive `snake_case` for functions and modules, and `PascalCase` for classes and dataclasses. Keep platform-specific code inside the matching adapter package rather than importing Win32, PyObjC, or DLL details into shared modules. There is no repo-enforced formatter or linter config, so match the surrounding code and keep changes small and readable.

## Testing Guidelines

Pytest is the test runner, configured via `pyproject.toml` to use `src` as `pythonpath` and `tests/` as the test root. Name tests `test_*.py`, and prefer focused tests that mirror the existing style in `tests/unit/`. Add integration tests only when a behavior crosses module boundaries or exercises real transport/session flow. Run the smallest relevant subset first, then the full suite before submitting changes.

## Commit & Pull Request Guidelines

Recent commits use short Conventional Commit-style prefixes such as `fix:`, `feat:`, `docs:`, `refactor:`, and `test:`. Keep commit subjects imperative and scoped. Pull requests should include a concise summary, the behavior changed, and validation notes such as test commands run. Include screenshots or platform notes when UI, Windows, or macOS behavior changes.

## Security & Configuration Tips

Do not commit local logs, build artifacts, or virtual environments. The vendored NVDA controller DLL lives at `src/adapters/windows/vendor/nvda/x64/nvdaControllerClient.dll`; keep packaging changes aligned with that path and the existing PyInstaller command.
