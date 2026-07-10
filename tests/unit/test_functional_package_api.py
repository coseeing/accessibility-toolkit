import importlib
import sys

import pytest


PUBLIC_SYMBOLS = {
    "accessibility_toolkit.scheduling": {"CancellationToken", "EventCallbacks", "ScheduledFuture", "Scheduler"},
    "accessibility_toolkit.events": {"AppEvent", "ErrorRaised", "SpeechEngineChanged", "InputCaptureChanged", "HotkeyCaptureChanged", "ClipboardAvailabilityChanged", "ModeChanged"},
    "accessibility_toolkit.input": {"HID", "KeyEvent", "CapturedKeyEvent", "KeyboardInputService"},
    "accessibility_toolkit.output": {"Capabilities", "ClipboardService", "QueuedService"},
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
