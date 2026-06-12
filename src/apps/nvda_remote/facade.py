from collections.abc import Callable
from typing import Any

from adapters.inputs.base import HotkeyCapture, InputCapture, KeyEventDecision
from application.input import InputActivationUseCase
from application.keyboard import KeyEventHandler
from application.output_service import SpeechOutputService
from application.services import ClipboardService
from application.state import ConnectionState, ControlState, RuntimeState
from interop.key.key_event import KeyEvent
from interop.protocol.connection_info import ConnectionInfo
from interop.protocol.messages import RemoteMessageType
from interop.protocol.routing.message_router import MessageRouter
from interop.protocol.session.remote_session import RemoteSession
from interop.protocol.transport.base import Transport

from apps.nvda_remote.use_cases import (
    NvdaRemoteControlModeUseCase,
    NvdaRemoteInputForwardingUseCase,
)
from apps.shared.mode_manager import ModeManager
from apps.shared.speech_settings_controller import SpeechSettingsController


class RemoteControlMode:
    mode_id = "remote_control"
    enter_vk = 0x7A
    exit_vk = 0x7A

    def __init__(self, control_mode, input_forwarding):
        self._control_mode = control_mode
        self._input_forwarding = input_forwarding

    def can_enter(self) -> bool:
        return True

    def enter(self) -> bool:
        self._control_mode.start_control()
        return True

    def exit(self) -> bool:
        self._control_mode.stop_control()
        self._input_forwarding.clear()
        return True

    def handle_key_event(self, event):
        return self._input_forwarding.handle(event)


class NvdaRemoteAppFacade(KeyEventHandler):
    _LOCAL_STOP_VK = 0x7A
    enter_vk = RemoteControlMode.enter_vk

    def __init__(
        self,
        *,
        transport: Transport,
        input_capture: InputCapture,
        hotkey_capture: HotkeyCapture,
        clipboard: ClipboardService,
        speech: SpeechOutputService,
        on_speech_backend_changed: Callable[[str], None] | None = None,
        main_thread_dispatch: Callable[[Callable[[], None]], None] | None = None,
    ) -> None:
        self.transport = transport
        self.input_capture = input_capture
        self.hotkey_capture = hotkey_capture
        self.clipboard = clipboard
        self.speech = speech
        self._on_speech_backend_changed = on_speech_backend_changed
        self.state = RuntimeState()
        self._status_listener: Callable[[dict[str, Any]], None] | None = None
        self._main_thread_dispatch = main_thread_dispatch or (lambda callback: callback())
        self._suppressed_keyups: set[int] = set()

        self.session = RemoteSession(
            transport=transport,
            on_status=self._on_status,
        )
        self.router = MessageRouter(
            on_speech=self.speech.speak,
            on_cancel=self.speech.cancel,
            on_pause=self.speech.pause,
            on_clipboard=self.clipboard.set_text,
            on_status=self._on_status,
        )

        self._control_mode = NvdaRemoteControlModeUseCase(
            state=self.state,
            notify_error=self._notify_error,
            notify_status=self._notify_status_listener,
        )
        self._input_forwarding = NvdaRemoteInputForwardingUseCase(
            is_connected=lambda: self.state.connection_state != ConnectionState.IDLE,
            is_controlling=lambda: self.state.control_state == ControlState.CONTROLLING,
            send_key=lambda payload: self.transport.send(RemoteMessageType.KEY, **payload),
            on_local_stop=self.stop_control,
            local_stop_vk=self._LOCAL_STOP_VK,
        )

        def _on_backend_changed_wrapper(backend_id: str) -> None:
            if self._on_speech_backend_changed is not None:
                self._on_speech_backend_changed(backend_id)

        self._speech_settings = SpeechSettingsController(
            speech=speech,
            on_backend_changed=_on_backend_changed_wrapper,
        )

        self._activation = InputActivationUseCase(
            input_capture=input_capture,
            hotkey_capture=hotkey_capture,
            is_active=lambda: self.state.control_state == ControlState.CONTROLLING,
            set_active=self._set_control_active,
            notify_error=self._notify_error,
        )
        self._mode_manager = ModeManager(
            activation=self._activation,
            notify_status=self._notify_status_listener,
        )
        self._mode_manager.register(
            RemoteControlMode(self._control_mode, self._input_forwarding)
        )

    def _set_control_active(self, active: bool) -> None:
        self.state.control_state = (
            ControlState.CONTROLLING if active else ControlState.CONNECTED
        )

    def _handle_idle_hotkey(self) -> None:
        if self.state.connection_state == ConnectionState.IDLE:
            return
        if self.state.control_state == ControlState.CONTROLLING:
            return
        self._main_thread_dispatch(self.start_control)

    def bind(self) -> None:
        self.input_capture.set_listener(self.handle_key_event)
        self.hotkey_capture.set_handler(self._handle_idle_hotkey)
        self.transport.set_message_handler(self._handle_transport_message)

    def connect(self, host: str, port: int, key: str, insecure: bool = False) -> None:
        self.session.connect(
            ConnectionInfo(hostname=host, port=port, key=key, insecure=insecure)
        )
        self.transport.start_reader()

    def disconnect(self) -> None:
        if self.state.control_state == ControlState.CONTROLLING:
            self.stop_control()
        elif self.state.connection_state != ConnectionState.IDLE:
            if self._mode_manager.active_mode_id is not None:
                self._mode_manager.exit_active_mode()
            self._activation.exit_active()
        self.transport.stop_reader()
        self.session.disconnect()

    def start_control(self) -> None:
        if self.state.connection_state == ConnectionState.IDLE:
            self._notify_error("Not connected")
            return
        self._mode_manager.activate_mode("remote_control")

    def stop_control(self) -> None:
        if self.state.control_state != ControlState.CONTROLLING:
            return
        self._mode_manager.exit_active_mode()
        self._suppressed_keyups.clear()
        self._input_forwarding.clear()

    def push_clipboard(self) -> None:
        self.transport.send(
            RemoteMessageType.SET_CLIPBOARD_TEXT,
            text=self.clipboard.get_text(),
        )

    def is_clipboard_available(self) -> bool:
        return bool(getattr(self.clipboard, "supported", True))

    def set_status_listener(
        self, listener: Callable[[dict[str, Any]], None] | None
    ) -> None:
        self._status_listener = listener

    def get_speech_backend_options(self) -> tuple[tuple[str, str], ...]:
        return self._speech_settings.get_backend_options()

    def get_selected_speech_backend(self) -> str:
        return self._speech_settings.get_selected_backend()

    def set_speech_backend(self, backend_id: str) -> None:
        self._speech_settings.set_backend(backend_id)
        self._notify_status_listener(
            {"kind": "speech_backend", "backend_id": backend_id}
        )

    def get_available_voices(self) -> tuple[tuple[str, str], ...]:
        return self._speech_settings.list_voices()

    def get_selected_voice(self) -> str | None:
        return self._speech_settings.get_voice()

    def set_selected_voice(self, voice_id: str) -> None:
        self._speech_settings.set_voice(voice_id)

    def get_rate(self) -> int | None:
        return self._speech_settings.get_rate()

    def set_rate(self, value: int) -> None:
        self._speech_settings.set_rate(value)

    def get_pitch(self) -> int | None:
        return self._speech_settings.get_pitch()

    def set_pitch(self, value: int) -> None:
        self._speech_settings.set_pitch(value)

    def get_volume(self) -> int | None:
        return self._speech_settings.get_volume()

    def set_volume(self, value: int) -> None:
        self._speech_settings.set_volume(value)

    def shutdown(self) -> None:
        self.disconnect()
        self.speech.shutdown()

    def handle_key_event(self, event: KeyEvent) -> KeyEventDecision:
        if not event.pressed and event.vk in self._suppressed_keyups:
            self._suppressed_keyups.discard(event.vk)
            return KeyEventDecision.SUPPRESS
        if event.pressed and event.vk == self._LOCAL_STOP_VK and self._mode_manager.active_mode_id is not None:
            self._suppressed_keyups.add(self._LOCAL_STOP_VK)
        return self._mode_manager.handle_key_event(event)

    def _handle_transport_message(self, payload: dict[str, Any]) -> None:
        if payload.get("type") == "transport_disconnected":
            self._on_status({"kind": "connection", "state": "idle"})
            return
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
                    self._activation.exit_active()
                    self._ensure_hotkey_started()
            case ConnectionState.IDLE.value:
                self._stop_capture()
                self._stop_hotkey()
                self.state.connection_state = ConnectionState.IDLE
                self.state.control_state = ControlState.IDLE
        self._notify_status_listener(status)

    def _notify_status_listener(self, status: dict[str, Any]) -> None:
        if self._status_listener is not None:
            self._main_thread_dispatch(lambda: self._status_listener(status))

    def _notify_error(self, message: str) -> None:
        self._notify_status_listener({"kind": "error", "message": message})

    def _ensure_capture_started(self) -> None:
        if not self.input_capture.running:
            self.input_capture.start()

    def _stop_capture(self) -> None:
        if self.input_capture.running:
            self.input_capture.stop()
        self._suppressed_keyups.clear()
        self._input_forwarding.clear()

    def _ensure_hotkey_started(self) -> None:
        if not self.hotkey_capture.running:
            self.hotkey_capture.start()

    def _stop_hotkey(self) -> None:
        if self.hotkey_capture.running:
            self.hotkey_capture.stop()
