from __future__ import annotations

import os
from pathlib import Path

from PyInstaller.building.api import BUNDLE, COLLECT, EXE
from PyInstaller.building.build_main import Analysis, PYZ
from PyInstaller.utils.hooks import collect_submodules


ROOT = Path(SPECPATH).resolve().parent
SRC = ROOT / "src"
DIST = ROOT / "dist"
BUILD = ROOT / "build" / "pyinstaller-macos"
APP_TARGET = os.environ.get("APP_TARGET", "all").strip().lower()
PYTTSX3_IMPORTS = collect_submodules("pyttsx3")


APPS = {
    "access8graph": {
        "name": "access8graph",
        "entry": SRC / "apps" / "access8graph" / "main.py",
        "bundle_identifier": "org.nvda-remote-client.access8graph",
        "hiddenimports": [
            "adapters.macos.permissions",
            "adapters.macos.event_tap",
            "adapters.macos.keyboard_hook",
            "adapters.macos.hotkey",
        ],
    },
    "key_echo": {
        "name": "key-echo-demo",
        "entry": SRC / "apps" / "key_echo" / "main.py",
        "bundle_identifier": "org.nvda-remote-client.key-echo-demo",
        "hiddenimports": [
            "adapters.macos.permissions",
            "adapters.macos.event_tap",
            "adapters.macos.keyboard_hook",
        ],
    },
    "nvda_remote": {
        "name": "nvda-remote-client",
        "entry": SRC / "apps" / "nvda_remote" / "main.py",
        "bundle_identifier": "org.nvda-remote-client.nvda-remote-client",
        "hiddenimports": [
            "adapters.macos.permissions",
            "adapters.macos.event_tap",
            "adapters.macos.keyboard_hook",
            "adapters.macos.hotkey",
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
        binaries=[],
        datas=[],
        hiddenimports=hiddenimports,
        hookspath=[],
        hooksconfig={},
        runtime_hooks=[],
        excludes=[],
        noarchive=False,
    )
    pyz = PYZ(analysis.pure)
    exe = EXE(
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
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    bundle = BUNDLE(
        exe,
        name=f"{app_name}.app",
        icon=None,
        bundle_identifier=settings["bundle_identifier"],
        info_plist={
            "CFBundleDisplayName": app_name,
            "CFBundleName": app_name,
            "NSAppleEventsUsageDescription": "Required for keyboard event handling.",
        },
    )
    return COLLECT(
        bundle,
        analysis.binaries,
        analysis.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name=app_name,
    )


for app_target, app_settings in APPS.items():
    build_app(app_target, app_settings)
