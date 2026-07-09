import importlib
import sys

_module = importlib.import_module("accessibility_toolkit.runtime.output")
sys.modules[__name__] = _module
