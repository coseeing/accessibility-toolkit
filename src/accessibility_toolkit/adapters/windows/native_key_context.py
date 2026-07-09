from dataclasses import dataclass


@dataclass(frozen=True)
class WindowsNativeKeyContext:
    vk_code: int
    scan_code: int
    extended: bool
