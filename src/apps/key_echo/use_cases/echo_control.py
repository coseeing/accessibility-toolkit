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
        self._echo_active = False

    def start_echo(self) -> None:
        if not self._input_service.running:
            try:
                self._input_service.start()
            except RuntimeError as error:
                self._notify_status({"kind": "error", "message": str(error)})
                return
        self._echo_active = True
        self._notify_status({"kind": "echo", "state": "running"})

    def stop_echo(self) -> None:
        self._echo_active = False
        self._notify_status({"kind": "echo", "state": "stopped"})

    def is_running(self) -> bool:
        return self._echo_active
