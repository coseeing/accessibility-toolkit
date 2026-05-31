from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KeyEvent:
    vk: int
    scan: int | None
    extended: bool
    pressed: bool

    def to_remote_payload(self) -> dict[str, int | bool | None]:
        return {
            "vk": self.vk,
            "scan": self.scan,
            "extended": self.extended,
            "pressed": self.pressed,
        }
