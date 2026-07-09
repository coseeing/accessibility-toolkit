import importlib
import sys

_module = importlib.import_module(
    "accessibility_toolkit.adapters.windows.nvda_controller"
)
sys.modules[__name__] = _module
