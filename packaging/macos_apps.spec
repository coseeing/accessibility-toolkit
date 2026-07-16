from __future__ import annotations

import os
from pathlib import Path

from PyInstaller.building.api import COLLECT, EXE
from PyInstaller.building.build_main import Analysis, PYZ
from PyInstaller.building.osx import BUNDLE
from PyInstaller.utils.hooks import collect_submodules


ROOT = Path(SPECPATH).resolve().parent
SRC = ROOT / "src"
NVDA_REMOTE_WAVES = SRC / "apps" / "nvda_remote" / "waves"
DIST = ROOT / "dist"
BUILD = ROOT / "build" / "pyinstaller-macos"
APP_TARGET = os.environ.get("APP_TARGET", "all").strip().lower()
PYTTSX3_IMPORTS = collect_submodules("pyttsx3")


APPS = {
    "access8graph": {
        "name": "access8graph",
        "entry": SRC / "apps" / "access8graph" / "main.py",
        "bundle_identifier": "org.coseeing.access8graph",
        "hiddenimports": [
            "accessibility_toolkit.input.macos.permissions",
            "accessibility_toolkit.input.macos.event_tap",
            "accessibility_toolkit.input.macos.keyboard_hook",
            "accessibility_toolkit.input.macos.hotkey",
        ],
    },
    "key_echo": {
        "name": "key-echo-demo",
        "entry": SRC / "apps" / "key_echo" / "main.py",
        "bundle_identifier": "org.coseeing.key-echo-demo",
        "hiddenimports": [
            "accessibility_toolkit.input.macos.permissions",
            "accessibility_toolkit.input.macos.event_tap",
            "accessibility_toolkit.input.macos.keyboard_hook",
            "accessibility_toolkit.input.macos.hotkey",
        ],
    },
    "nvda_remote": {
        "name": "nvda_remote",
        "entry": SRC / "apps" / "nvda_remote" / "main.py",
        "bundle_identifier": "org.coseeing.accessibility-toolkit",
        "hiddenimports": [
            "accessibility_toolkit.input.macos.permissions",
            "accessibility_toolkit.input.macos.event_tap",
            "accessibility_toolkit.input.macos.keyboard_hook",
            "accessibility_toolkit.input.macos.hotkey",
        ],
        "datas": [(str(NVDA_REMOTE_WAVES), "apps/nvda_remote/waves")],
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
        datas=settings.get("datas", []),
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
        [],
        name=app_name,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        exclude_binaries=True,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    coll = COLLECT(
        exe,
        analysis.binaries,
        analysis.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name=app_name,
    )
    return BUNDLE(
        coll,
        name=f"{app_name}.app",
        icon=None,
        bundle_identifier=settings["bundle_identifier"],
        info_plist={
            "CFBundleDisplayName": app_name,
            "CFBundleName": app_name,
            "NSAppleEventsUsageDescription": "Required for keyboard event handling.",
        },
    )


import subprocess

for app_target, app_settings in APPS.items():
    build_app(app_target, app_settings)

for app_target, app_settings in APPS.items():
    if not should_build(app_target):
        continue
    app_name = app_settings["name"]
    zip_path = DIST / f"{app_name}.zip"
    zip_path.unlink(missing_ok=True)
    subprocess.run(
        ["zip", "-ry", str(zip_path), f"{app_name}.app"],
        cwd=str(DIST),
        check=True,
    )
    print(f"Zipped: {zip_path}")
