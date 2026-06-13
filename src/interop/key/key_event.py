from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KeyEvent:
    usage_page: int
    usage: int
    pressed: bool
    vk: int | None = None
    scan: int | None = None
    extended: bool = False

    def to_local_payload(self) -> dict[str, int | bool]:
        return {
            "usage_page": self.usage_page,
            "usage": self.usage,
            "pressed": self.pressed,
        }

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, KeyEvent):
            return NotImplemented
        return (
            self.usage_page == other.usage_page
            and self.usage == other.usage
            and self.pressed == other.pressed
        )

    def __hash__(self) -> int:
        return hash((self.usage_page, self.usage, self.pressed))
