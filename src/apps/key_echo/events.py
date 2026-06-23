from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EchoStateChanged:
    running: bool
