from dataclasses import dataclass
from typing import Any, Callable


TrustedChecker = Callable[[Any], bool]


@dataclass(slots=True)
class AccessibilityPermissions:
    checker: TrustedChecker
    prompt_key: Any = None
    true_value: Any = True

    def is_trusted(self, *, prompt: bool = False) -> bool:
        if not prompt:
            return bool(self.checker(None))
        if self.prompt_key is None:
            raise RuntimeError("Prompt key is required when prompt=True")
        return bool(self.checker({self.prompt_key: self.true_value}))
