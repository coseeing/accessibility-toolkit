from typing import Any

from adapters.inputs.base import HotkeyCapture, InputCapture, KeyEventDecision
from adapters.outputs.speech import NullSpeechOutput, SpeechOutput
from application.speech_backends import SpeechBackendManager
from application.services import ClipboardService, OutputManager
from application.state import ConnectionState, ControlState, RuntimeState
from remote_core.connection_info import ConnectionInfo
from remote_core.models.keys import KeyEvent
from remote_core.protocol import RemoteMessageType
from remote_core.routing.message_router import MessageRouter
from remote_core.session.remote_session import RemoteSession
from remote_core.transport.base import Transport


class ClientController:
    _LOCAL_STOP_VK = 0x7A  # F11

    def __init__(
        self,
        transport: Transport,
        input_capture: InputCapture,
        hotkey_capture: HotkeyCapture,
        clipboard: ClipboardService,
        speech_output: SpeechOutput,
        speech_backend_manager: SpeechBackendManager | None = None,
        on_speech_backend_changed=None,
        main_thread_dispatch=None,
    ) -> None:
        self.transport = transport
        self.input_capture = input_capture
        self.hotkey_capture = hotkey_capture
        self.clipboard = clipboard
        self.state = RuntimeState()
        self._status_listener = None
        self._speech_backend_manager = speech_backend_manager
        self._on_speech_backend_changed = on_speech_backend_changed
        self._main_thread_dispatch = main_thread_dispatch or (lambda callback: callback())
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
            on_cancel=self.output_manager.handle_cancel,
            on_pause=self.output_manager.handle_pause,
            on_clipboard=self.output_manager.handle_clipboard,
            on_status=self._on_status,
        )
        self._suppressed_keyups: set[int] = set()
        self.input_capture.set_listener(self._forward_key_event)
        self.hotkey_capture.set_handler(self._handle_hotkey_toggle)
        set_message_handler = getattr(self.transport, "set_message_handler", None)
        if set_message_handler is not None:
            set_message_handler(self._handle_transport_message)

    @classmethod
    def build_for_tests(
        cls,
        transport: Transport,
        input_capture: InputCapture,
        hotkey_capture: HotkeyCapture,
        clipboard: ClipboardService,
        speech_backend_manager: SpeechBackendManager | None = None,
        main_thread_dispatch=None,
    ) -> "ClientController":
        speech_output: SpeechOutput
        if speech_backend_manager is None:
            speech_output = NullSpeechOutput()
        else:
            speech_output = speech_backend_manager.current_output
        return cls(
            transport=transport,
            input_capture=input_capture,
            hotkey_capture=hotkey_capture,
            clipboard=clipboard,
            speech_output=speech_output,
            speech_backend_manager=speech_backend_manager,
            main_thread_dispatch=main_thread_dispatch,
        )

    def connect(self, host: str, port: int, key: str, insecure: bool = False) -> None:
        self.session.connect(
            ConnectionInfo(hostname=host, port=port, key=key, insecure=insecure)
        )
        start_reader = getattr(self.transport, "start_reader", None)
        if start_reader is not None:
            start_reader()

    def disconnect(self) -> None:
        if self.state.control_state == ControlState.CONTROLLING:
            self.stop_control()
        elif self.state.connection_state != ConnectionState.IDLE:
            self._stop_capture()
        stop_reader = getattr(self.transport, "stop_reader", None)
        if stop_reader is not None:
            stop_reader()
        self.session.disconnect()

    def start_control(self) -> None:
        self._stop_hotkey()
        self._ensure_capture_started()
        self.state.control_state = ControlState.CONTROLLING
        self._notify_status_listener(
            {"kind": "control", "state": ControlState.CONTROLLING.value}
        )

    def stop_control(self) -> None:
        self._stop_capture()
        self.state.control_state = ControlState.SUSPENDED
        if self.state.connection_state != ConnectionState.IDLE:
            self._ensure_hotkey_started()
        self._notify_status_listener(
            {"kind": "control", "state": ControlState.SUSPENDED.value}
        )

    def push_clipboard(self) -> None:
        self.output_manager.push_clipboard(self.transport)

    def set_status_listener(self, listener) -> None:
        self._status_listener = listener

    def get_speech_backend_options(self) -> tuple[tuple[str, str], ...]:
        if self._speech_backend_manager is None:
            return ()
        return self._speech_backend_manager.backend_choices()

    def get_selected_speech_backend(self) -> str | None:
        if self._speech_backend_manager is None:
            return None
        return self._speech_backend_manager.selected_backend_id

    def set_speech_backend(self, backend_id: str) -> None:
        if self._speech_backend_manager is None:
            raise RuntimeError("Speech backend switching is not configured")
        new_output = self._speech_backend_manager.set_backend(backend_id)
        self.output_manager.set_speech_output(new_output, cancel_current=False)
        if self._on_speech_backend_changed is not None:
            self._on_speech_backend_changed(backend_id)
        self._notify_status_listener(
            {"kind": "speech_backend", "backend_id": backend_id}
        )

    def get_available_voices(self) -> tuple[tuple[str, str], ...]:
        return self.output_manager.speech_output.list_voices()

    def get_selected_voice(self) -> str | None:
        return self.output_manager.speech_output.get_voice()

    def set_selected_voice(self, voice_id: str) -> None:
        self.output_manager.speech_output.set_voice(voice_id)

    def get_rate(self) -> int | None:
        return self.output_manager.speech_output.get_rate()

    def set_rate(self, value: int) -> None:
        self.output_manager.speech_output.set_rate(value)

    def get_pitch(self) -> int | None:
        return self.output_manager.speech_output.get_pitch()

    def set_pitch(self, value: int) -> None:
        self.output_manager.speech_output.set_pitch(value)

    def get_volume(self) -> int | None:
        return self.output_manager.speech_output.get_volume()

    def set_volume(self, value: int) -> None:
        self.output_manager.speech_output.set_volume(value)

    def _forward_key_event(self, event: KeyEvent) -> KeyEventDecision:
        if not event.pressed and event.vk in self._suppressed_keyups:
            self._suppressed_keyups.discard(event.vk)
            return KeyEventDecision.LOCAL_ONLY_SUPPRESS
        if self.state.connection_state == ConnectionState.IDLE:
            return KeyEventDecision.PASS_THROUGH
        if event.vk == self._LOCAL_STOP_VK:
            if event.pressed:
                self._suppressed_keyups.add(event.vk)
                self.stop_control()
            return KeyEventDecision.LOCAL_ONLY_SUPPRESS
        if self.state.control_state != ControlState.CONTROLLING:
            return KeyEventDecision.PASS_THROUGH
        self.transport.send(RemoteMessageType.KEY, **event.to_remote_payload())
        return KeyEventDecision.FORWARD_AND_SUPPRESS

    def _handle_transport_message(self, payload: dict[str, Any]) -> None:
        if self.session.handle_message(payload):
            return
        self.router.handle_message(payload)

    def _on_status(self, status: dict[str, Any]) -> None:
        if status.get("kind") != "connection":
            self._notify_status_listener(status)
            return

        match status.get("state"):
            case ConnectionState.CONNECTED.value:
                self.state.connection_state = ConnectionState.CONNECTED
                if self.state.control_state != ControlState.CONTROLLING:
                    self.state.control_state = ControlState.CONNECTED
                    self._ensure_hotkey_started()
            case ConnectionState.IDLE.value:
                self._stop_capture()
                self._stop_hotkey()
                self.state.connection_state = ConnectionState.IDLE
                self.state.control_state = ControlState.IDLE
        self._notify_status_listener(status)

    def _notify_status_listener(self, status: dict[str, Any]) -> None:
        if self._status_listener is not None:
            self._status_listener(status)

    def _ensure_capture_started(self) -> None:
        if not getattr(self.input_capture, "running", False):
            self.input_capture.start()

    def _stop_capture(self) -> None:
        if getattr(self.input_capture, "running", False):
            self.input_capture.stop()
        self._suppressed_keyups.clear()

    def _ensure_hotkey_started(self) -> None:
        if not getattr(self.hotkey_capture, "running", False):
            self.hotkey_capture.start()

    def _stop_hotkey(self) -> None:
        if getattr(self.hotkey_capture, "running", False):
            self.hotkey_capture.stop()

    def _handle_hotkey_toggle(self) -> None:
        if self.state.connection_state == ConnectionState.IDLE:
            return
        self._main_thread_dispatch(self._toggle_control_from_hotkey)

    def _toggle_control_from_hotkey(self) -> None:
        if self.state.connection_state == ConnectionState.IDLE:
            return
        if self.state.control_state == ControlState.CONTROLLING:
            self.stop_control()
            return
        self.start_control()
