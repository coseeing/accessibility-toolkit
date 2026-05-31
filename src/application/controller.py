from typing import Any

from adapters.inputs.base import InputCapture
from adapters.outputs.speech import NullSpeechOutput, SpeechOutput
from application.services import ClipboardService, OutputManager
from application.state import ConnectionState, ControlState, RuntimeState
from remote_core.connection_info import ConnectionInfo
from remote_core.models.keys import KeyEvent
from remote_core.protocol import RemoteMessageType
from remote_core.routing.message_router import MessageRouter
from remote_core.session.remote_session import RemoteSession
from remote_core.transport.base import Transport


class ClientController:
    def __init__(
        self,
        transport: Transport,
        input_capture: InputCapture,
        clipboard: ClipboardService,
        speech_output: SpeechOutput,
    ) -> None:
        self.transport = transport
        self.input_capture = input_capture
        self.clipboard = clipboard
        self.state = RuntimeState()
        self.output_manager = OutputManager(
            speech_output=speech_output,
            clipboard=clipboard,
        )
        self.session = RemoteSession(
            transport=transport,
            on_status=self._on_status,
        )
        self.router = MessageRouter(
            on_speech=self.output_manager.handle_speech,
            on_clipboard=self.output_manager.handle_clipboard,
            on_status=self._on_status,
        )
        self.input_capture.set_listener(self._forward_key_event)
        set_message_handler = getattr(self.transport, "set_message_handler", None)
        if set_message_handler is not None:
            set_message_handler(self._handle_transport_message)

    @classmethod
    def build_for_tests(
        cls,
        transport: Transport,
        input_capture: InputCapture,
        clipboard: ClipboardService,
    ) -> "ClientController":
        return cls(
            transport=transport,
            input_capture=input_capture,
            clipboard=clipboard,
            speech_output=NullSpeechOutput(),
        )

    def connect(self, host: str, port: int, key: str) -> None:
        self.session.connect(ConnectionInfo(hostname=host, port=port, key=key))

    def start_control(self) -> None:
        self.input_capture.start()
        self.state.control_state = ControlState.CONTROLLING

    def stop_control(self) -> None:
        self.input_capture.stop()
        self.state.control_state = ControlState.SUSPENDED

    def push_clipboard(self) -> None:
        self.output_manager.push_clipboard(self.transport)

    def _forward_key_event(self, event: KeyEvent) -> None:
        if self.state.control_state != ControlState.CONTROLLING:
            return
        self.transport.send(RemoteMessageType.KEY, **event.to_remote_payload())

    def _handle_transport_message(self, payload: dict[str, Any]) -> None:
        if self.session.handle_message(payload):
            return
        self.router.handle_message(payload)

    def _on_status(self, status: dict[str, Any]) -> None:
        if status.get("kind") != "connection":
            return

        match status.get("state"):
            case ConnectionState.CONNECTED.value:
                self.state.connection_state = ConnectionState.CONNECTED
                if self.state.control_state != ControlState.CONTROLLING:
                    self.state.control_state = ControlState.CONNECTED
            case ConnectionState.IDLE.value:
                self.state.connection_state = ConnectionState.IDLE
                self.state.control_state = ControlState.IDLE
