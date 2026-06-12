from collections.abc import Callable


class KeyEchoControlUseCase:
    def __init__(
        self,
        *,
        notify_status: Callable[[dict[str, str]], None],
    ) -> None:
        self._notify_status = notify_status
        self._echo_active = False

    def start_echo(self) -> None:
        self._echo_active = True
        self._notify_status({"kind": "echo", "state": "running"})

    def stop_echo(self) -> None:
        self._echo_active = False
        self._notify_status({"kind": "echo", "state": "stopped"})

    def is_running(self) -> bool:
        return self._echo_active
