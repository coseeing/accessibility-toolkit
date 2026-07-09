import pytest

import accessibility_toolkit.runtime.platform as _bp


def _reset_bootstrap_platform_lazy_globals() -> None:
    _bp._WindowsKeyboardCapture = None
    _bp._WindowsHotkeyCapture = None
    _bp._WindowsClipboardService = None
    _bp._NvdaControllerSpeechOutput = None
    _bp._AccessibilityPermissions = None
    _bp._MacOSEventTapManager = None
    _bp._MacOSEventTapBackend = None
    _bp._MacOSKeyboardCapture = None
    _bp._MacOSHotkeyCapture = None
    _bp._macos_event_tap_manager_instance = None


@pytest.fixture(autouse=True)
def reset_bootstrap_platform_lazy_globals():
    _reset_bootstrap_platform_lazy_globals()
    yield
    _reset_bootstrap_platform_lazy_globals()
