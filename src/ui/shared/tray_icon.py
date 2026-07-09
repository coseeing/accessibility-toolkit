import importlib
import sys

_module = importlib.import_module("accessibility_toolkit_wx.tray.tray_icon")
_module = importlib.reload(_module)
sys.modules[__name__] = _module
