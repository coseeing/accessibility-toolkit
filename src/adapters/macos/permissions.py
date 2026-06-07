from dataclasses import dataclass
from typing import Any, Callable

try:  # pragma: no cover - exercised on macOS
    from ApplicationServices import (
        AXIsProcessTrustedWithOptions,
        kAXTrustedCheckOptionPrompt,
    )
    from Quartz import (
        CGPreflightListenEventAccess,
        CGRequestListenEventAccess,
    )
except ImportError:  # pragma: no cover - non-macOS test environment
    AXIsProcessTrustedWithOptions = None
    kAXTrustedCheckOptionPrompt = None
    CGPreflightListenEventAccess = None
    CGRequestListenEventAccess = None


TrustedChecker = Callable[[Any], bool]


@dataclass(slots=True)
class AccessibilityPermissions:
    checker: TrustedChecker
    prompt_key: Any = None
    true_value: Any = True
    listen_checker: Callable[[], bool] | None = None
    listen_requester: Callable[[], bool] | None = None

    @classmethod
    def load_default(cls) -> "AccessibilityPermissions":
        if AXIsProcessTrustedWithOptions is None:
            raise RuntimeError("PyObjC ApplicationServices is required on macOS")
        return cls(
            checker=AXIsProcessTrustedWithOptions,
            prompt_key=kAXTrustedCheckOptionPrompt,
            true_value=True,
            listen_checker=CGPreflightListenEventAccess,
            listen_requester=CGRequestListenEventAccess,
        )

    def is_trusted(self, *, prompt: bool = False) -> bool:
        if not prompt:
            return bool(self.checker(None))
        if self.prompt_key is None:
            raise RuntimeError("Prompt key is required when prompt=True")
        return bool(self.checker({self.prompt_key: self.true_value}))

    def has_listen_event_access(self, *, prompt: bool = False) -> bool:
        if self.listen_checker is None:
            return True
        if self.listen_checker():
            return True
        if not prompt or self.listen_requester is None:
            return False
        return bool(self.listen_requester())
