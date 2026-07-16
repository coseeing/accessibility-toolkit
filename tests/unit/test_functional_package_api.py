import importlib
import sys
import tomllib
from pathlib import Path

import pytest


PUBLIC_SYMBOLS = {
    "accessibility_toolkit.scheduling": {"CancellationToken", "EventCallbacks", "ScheduledFuture", "Scheduler"},
    "accessibility_toolkit.events": {"AppEvent", "ErrorRaised", "SpeechEngineChanged", "InputCaptureChanged", "HotkeyCaptureChanged", "ClipboardAvailabilityChanged", "ModeChanged"},
    "accessibility_toolkit.input": {"HID", "KeyEvent", "CapturedKeyEvent", "KeyboardInputService"},
    "accessibility_toolkit.input.windows": {
        "WindowsHotkeyCapture",
        "WindowsKeyboardCapture",
        "WindowsKeyboardHook",
        "WindowsNativeKeyContext",
        "key_event_from_windows",
    },
    "accessibility_toolkit.input.macos": {
        "AccessibilityPermissions",
        "MacOSEventTapManager",
        "MacOSHotkeyCapture",
        "MacOSKeyboardCapture",
        "QuartzEventTapBackend",
        "RawMacKeyEvent",
        "key_event_from_macos",
    },
    "accessibility_toolkit.output": {"Capabilities", "ClipboardService", "QueuedService", "WaveOutput"},
    "accessibility_toolkit.output.speech": {"SpeechSequence", "SpeechService", "SpeechEngineOption"},
    "accessibility_toolkit.interaction": {"ActivationMode", "ModeManager"},
    "accessibility_toolkit.remote": {"ConnectionInfo", "ConnectionMode", "JSONSerializer", "RemoteMessageType"},
    "accessibility_toolkit.runtime": {"AppRuntimeParts", "OutputServices", "PlatformProvider", "PlatformServices", "build_app_runtime_parts", "build_output_services"},
}


@pytest.mark.parametrize(("module_name", "expected"), PUBLIC_SYMBOLS.items())
def test_public_package_exports(module_name, expected):
    module = importlib.import_module(module_name)
    assert expected <= set(module.__all__)
    assert all(hasattr(module, name) for name in expected)


@pytest.mark.parametrize("name", ["application", "application_support", "interop", "adapters"])
def test_removed_technical_package_is_not_importable(name):
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(f"accessibility_toolkit.{name}")


@pytest.mark.parametrize("name", ["input", "output", "scheduling", "interaction", "events", "remote"])
def test_feature_import_does_not_load_runtime(name):
    sys.modules.pop("accessibility_toolkit.runtime", None)
    importlib.import_module(f"accessibility_toolkit.{name}")
    assert "accessibility_toolkit.runtime" not in sys.modules


def test_core_package_discovery_excludes_wx():
    core_toml = Path(__file__).parents[2] / "packages" / "accessibility-toolkit-core" / "pyproject.toml"
    data = tomllib.loads(core_toml.read_text())
    include = data["tool"]["setuptools"]["packages"]["find"]["include"]
    assert "accessibility_toolkit_wx" not in include
    assert "accessibility_toolkit" in include


def test_package_data_uses_output_speech_windows_path():
    core_toml = Path(__file__).parents[2] / "packages" / "accessibility-toolkit-core" / "pyproject.toml"
    data = tomllib.loads(core_toml.read_text())
    pd = data["tool"]["setuptools"]["package-data"]
    assert "accessibility_toolkit.output.speech.windows" in pd
    assert "adapters.windows" not in str(data)
    root_data = tomllib.loads(
        (Path(__file__).parents[2] / "pyproject.toml").read_text()
    )["tool"]["setuptools"]["package-data"]
    assert root_data["apps.nvda_remote"] == [
        "waves/*.wav",
        "waves/NOTICE.md",
        "waves/NVDA-COPYING.txt",
    ]
