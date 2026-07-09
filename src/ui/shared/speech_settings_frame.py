import importlib
import sys

_module = importlib.import_module(
    "accessibility_toolkit_wx.speech.speech_settings_frame"
)
_module = importlib.reload(_module)
sys.modules[__name__] = _module
