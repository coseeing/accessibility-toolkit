from collections.abc import Callable

from application.keyboard import KeyboardInputService


class KeyEchoControlUseCase:
    def __init__(
        self,
        *,
        input_service: KeyboardInputService,
        notify_status: Callable[[dict[str, str]], None],
    ) -> None:
        self._input_service = input_service
        self._notify_status = notify_status

    def start_echo(self) -> None:
        if not self._input_service.running:
            self._input_service.start()
        self._notify_status({"kind": "echo", "state": "running"})

    def stop_echo(self) -> None:
        if self._input_service.running:
            self._input_service.stop()
        self._notify_status({"kind": "echo", "state": "stopped"})

    def is_running(self) -> bool:
        return self._input_service.running
