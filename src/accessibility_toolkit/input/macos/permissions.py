from dataclasses import dataclass
from typing import Any, Callable


try:
    from ApplicationServices import (
        AXIsProcessTrustedWithOptions,
        kAXTrustedCheckOptionPrompt,
    )
except ImportError:
    AXIsProcessTrustedWithOptions = None
    kAXTrustedCheckOptionPrompt = None

try:
    from Quartz import (
        CGPreflightListenEventAccess,
        CGRequestListenEventAccess,
    )
except ImportError:
    CGPreflightListenEventAccess = None
    CGRequestListenEventAccess = None


TrustedChecker = Callable[[Any], bool]


@dataclass(slots=True)
class AccessibilityPermissions:
    checker: TrustedChecker
    listen_checker: TrustedChecker | None = None
    prompt_key: Any = None
    true_value: Any = True

    @classmethod
    def load_default(cls) -> "AccessibilityPermissions":
        if AXIsProcessTrustedWithOptions is None:
            raise RuntimeError("PyObjC ApplicationServices is required on macOS")
        listen = None
        if CGPreflightListenEventAccess is not None:
            listen = CGPreflightListenEventAccess
        return cls(
            checker=AXIsProcessTrustedWithOptions,
            listen_checker=listen,
            prompt_key=kAXTrustedCheckOptionPrompt,
            true_value=True,
        )

    def is_trusted(self, *, prompt: bool = False) -> bool:
        if not prompt:
            return bool(self.checker(None))
        if self.prompt_key is None:
            raise RuntimeError("Prompt key is required when prompt=True")
        return bool(self.checker({self.prompt_key: self.true_value}))

    def has_listen_event_access(self, *, prompt: bool = False) -> bool:
        if self.listen_checker is None:
            return self.is_trusted(prompt=prompt)
        granted = bool(self.listen_checker())
        if not granted and prompt and CGRequestListenEventAccess is not None:
            CGRequestListenEventAccess()
            granted = bool(self.listen_checker())
        return granted
