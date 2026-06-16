from __future__ import annotations

import os
from pathlib import Path

from PyInstaller.building.api import EXE
from PyInstaller.building.build_main import Analysis, PYZ
from PyInstaller.utils.hooks import collect_submodules


ROOT = Path(SPECPATH).resolve().parent
SRC = ROOT / "src"
APP_TARGET = os.environ.get("APP_TARGET", "all").strip().lower()
PYTTSX3_IMPORTS = collect_submodules("pyttsx3")
NVDA_DLL = SRC / "adapters" / "windows" / "vendor" / "nvda" / "x64" / "nvdaControllerClient.dll"


APPS = {
    "access8graph": {
        "name": "access8graph",
        "entry": SRC / "apps" / "access8graph" / "main.py",
        "hiddenimports": [
            "adapters.windows.keyboard_hook",
            "adapters.windows.hotkey",
            "adapters.windows.nvda_controller",
        ],
    },
    "key_echo": {
        "name": "key-echo-demo",
        "entry": SRC / "apps" / "key_echo" / "main.py",
        "hiddenimports": [
            "adapters.windows.keyboard_hook",
            "adapters.windows.hotkey",
            "adapters.windows.nvda_controller",
        ],
    },
    "nvda_remote": {
        "name": "nvda_remote",
        "entry": SRC / "apps" / "nvda_remote" / "main.py",
        "hiddenimports": [
            "adapters.windows.keyboard_hook",
            "adapters.windows.hotkey",
            "adapters.windows.clipboard",
            "adapters.windows.nvda_controller",
        ],
    },
}


if APP_TARGET not in {"all", *APPS.keys()}:
    raise SystemExit(
        f"Unsupported APP_TARGET={APP_TARGET!r}; expected one of: all, "
        + ", ".join(sorted(APPS))
    )


def should_build(target: str) -> bool:
    return APP_TARGET in {"all", target}


def build_app(target: str, settings: dict[str, object]):
    if not should_build(target):
        return None

    app_name = settings["name"]
    entry = str(settings["entry"])
    hiddenimports = [*PYTTSX3_IMPORTS, *settings["hiddenimports"]]

    analysis = Analysis(
        [entry],
        pathex=[str(SRC)],
        binaries=[(str(NVDA_DLL), "adapters/windows/vendor/nvda/x64")],
        datas=[],
        hiddenimports=hiddenimports,
        hookspath=[],
        hooksconfig={},
        runtime_hooks=[],
        excludes=[],
        noarchive=False,
    )
    pyz = PYZ(analysis.pure)
    return EXE(
        pyz,
        analysis.scripts,
        analysis.binaries,
        analysis.datas,
        [],
        name=app_name,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
    )


for app_target, app_settings in APPS.items():
    build_app(app_target, app_settings)
