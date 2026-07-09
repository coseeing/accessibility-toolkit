import importlib
import sys

_module = importlib.import_module("accessibility_toolkit_wx.shell.tool_app_shell")
_module = importlib.reload(_module)
sys.modules[__name__] = _module
