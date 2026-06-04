import ssl

import wx


class MainFrame(wx.Frame):
    _DEFAULT_BACKEND_OPTIONS = (
        ("nvda_controller", "NVDA Controller"),
        ("pyttsx3", "pyttsx3"),
    )

    def __init__(self, controller):
        super().__init__(parent=None, title="NVDA Remote Client")
        self.controller = controller
        if self.controller is not None and hasattr(self.controller, "set_status_listener"):
            self.controller.set_status_listener(self._on_controller_status)

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.host_ctrl = wx.TextCtrl(panel)
        self.port_ctrl = wx.TextCtrl(panel, value="6837")
        self.key_ctrl = wx.TextCtrl(panel)
        self.connect_button = wx.Button(panel, label="Connect")
        self.control_button = wx.Button(panel, label="Start Control")
        self.clipboard_button = wx.Button(panel, label="Push Clipboard")
        self._speech_backend_options = self._get_speech_backend_options()
        self.speech_backend_choice = wx.Choice(
            panel,
            choices=[label for _backend_id, label in self._speech_backend_options],
        )
        self._voice_options = self._get_available_voices()
        self.voice_choice = wx.Choice(
            panel,
            choices=[label for _voice_id, label in self._voice_options],
        )
        self.rate_ctrl = wx.TextCtrl(panel, value="")
        self.pitch_ctrl = wx.TextCtrl(panel, value="")
        self.volume_ctrl = wx.TextCtrl(panel, value="")

        for widget in (
            self.host_ctrl,
            self.port_ctrl,
            self.key_ctrl,
            self.connect_button,
            self.control_button,
            self.clipboard_button,
            self.speech_backend_choice,
            self.voice_choice,
            self.rate_ctrl,
            self.pitch_ctrl,
            self.volume_ctrl,
        ):
            sizer.Add(widget, 0, wx.EXPAND | wx.ALL, 4)

        panel.SetSizer(sizer)

        self.connect_button.Bind(wx.EVT_BUTTON, self._on_connect)
        self.control_button.Bind(wx.EVT_BUTTON, self._on_start_control)
        self.clipboard_button.Bind(wx.EVT_BUTTON, self._on_push_clipboard)
        self.speech_backend_choice.Bind(wx.EVT_CHOICE, self._on_speech_backend_change)
        self.voice_choice.Bind(wx.EVT_CHOICE, self._on_voice_change)
        self.rate_ctrl.Bind(wx.EVT_TEXT, self._on_rate_change)
        self.pitch_ctrl.Bind(wx.EVT_TEXT, self._on_pitch_change)
        self.volume_ctrl.Bind(wx.EVT_TEXT, self._on_volume_change)
        self._sync_connect_button_label()
        self._sync_control_button()
        self._sync_connection_fields()
        self._sync_clipboard_button()
        self._sync_speech_backend_choice()
        self._sync_speech_controls()

    def _on_connect(self, event):
        if self.controller is None:
            return
        if self._is_connected():
            self.controller.disconnect()
            self._sync_connect_button_label()
            self._sync_control_button()
            self._sync_connection_fields()
            self._sync_clipboard_button()
            return
        host = self.host_ctrl.GetValue()
        port = int(self.port_ctrl.GetValue())
        key = self.key_ctrl.GetValue()
        try:
            self.controller.connect(host, port, key)
        except ssl.SSLCertVerificationError:
            self.controller.connect(host, port, key, insecure=True)
        except Exception as error:
            wx.MessageBox(
                str(error),
                "Connection Error",
                wx.OK | wx.ICON_ERROR,
            )
        self._sync_connect_button_label()
        self._sync_control_button()
        self._sync_connection_fields()
        self._sync_clipboard_button()

    def _on_start_control(self, event):
        if self.controller is None:
            return
        if self._is_controlling():
            self.controller.stop_control()
        else:
            self.controller.start_control()
        self._sync_control_button()

    def _on_push_clipboard(self, event):
        if self.controller is None:
            return
        self.controller.push_clipboard()

    def _on_speech_backend_change(self, event):
        if self.controller is None or not hasattr(self.controller, "set_speech_backend"):
            return
        backend_id = self._backend_id_for_selection(self.speech_backend_choice.GetSelection())
        if backend_id is None:
            return
        try:
            self.controller.set_speech_backend(backend_id)
        except Exception as error:
            self._sync_speech_backend_choice()
            wx.MessageBox(
                str(error),
                "Speech Backend Error",
                wx.OK | wx.ICON_ERROR,
            )
            return
        self._sync_speech_backend_choice()
        self._sync_speech_controls()

    def _on_voice_change(self, event):
        if self.controller is None or not hasattr(self.controller, "set_selected_voice"):
            return
        voice_id = self._voice_id_for_selection(self.voice_choice.GetSelection())
        if voice_id is not None:
            self.controller.set_selected_voice(voice_id)

    def _on_rate_change(self, event):
        self._set_int_control_value(self.rate_ctrl, "set_rate")

    def _on_pitch_change(self, event):
        self._set_int_control_value(self.pitch_ctrl, "set_pitch")

    def _on_volume_change(self, event):
        self._set_int_control_value(self.volume_ctrl, "set_volume")

    def _is_connected(self) -> bool:
        if self.controller is None or not hasattr(self.controller, "state"):
            return False
        return getattr(self.controller.state, "connection_state", "idle") != "idle"

    def _is_controlling(self) -> bool:
        if self.controller is None or not hasattr(self.controller, "state"):
            return False
        return getattr(self.controller.state, "control_state", "idle") == "controlling"

    def _sync_connect_button_label(self) -> None:
        self.connect_button.SetLabel("Disconnect" if self._is_connected() else "Connect")

    def _sync_control_button(self) -> None:
        if not self._is_connected():
            self.control_button.SetLabel("Start Control")
            self.control_button.Disable()
            return
        self.control_button.Enable(True)
        self.control_button.SetLabel(
            "Stop Control" if self._is_controlling() else "Start Control"
        )

    def _sync_connection_fields(self) -> None:
        enabled = not self._is_connected()
        self.host_ctrl.Enable(enabled)
        self.port_ctrl.Enable(enabled)
        self.key_ctrl.Enable(enabled)

    def _sync_clipboard_button(self) -> None:
        self.clipboard_button.Enable(self._is_connected())

    def _sync_speech_backend_choice(self) -> None:
        selected_backend = self._get_selected_speech_backend()
        for index, (backend_id, _label) in enumerate(self._speech_backend_options):
            if backend_id == selected_backend:
                self.speech_backend_choice.SetSelection(index)
                return
        if self._speech_backend_options:
            self.speech_backend_choice.SetSelection(0)

    def _sync_speech_controls(self) -> None:
        self._voice_options = self._get_available_voices()
        self.voice_choice.choices = [label for _voice_id, label in self._voice_options]
        self.voice_choice.SetSelection(self._voice_selection_for_current_value())
        self.rate_ctrl.SetValue(self._stringify_optional_int(self._get_rate()))
        self.pitch_ctrl.SetValue(self._stringify_optional_int(self._get_pitch()))
        self.volume_ctrl.SetValue(self._stringify_optional_int(self._get_volume()))

    def _on_controller_status(self, _status) -> None:
        self._sync_connect_button_label()
        self._sync_control_button()
        self._sync_connection_fields()
        self._sync_clipboard_button()
        self._sync_speech_backend_choice()
        self._sync_speech_controls()

    def _get_speech_backend_options(self) -> tuple[tuple[str, str], ...]:
        if self.controller is None or not hasattr(self.controller, "get_speech_backend_options"):
            return self._DEFAULT_BACKEND_OPTIONS
        options = self.controller.get_speech_backend_options()
        return options or self._DEFAULT_BACKEND_OPTIONS

    def _get_selected_speech_backend(self) -> str:
        if self.controller is None or not hasattr(self.controller, "get_selected_speech_backend"):
            return self._DEFAULT_BACKEND_OPTIONS[0][0]
        selected = self.controller.get_selected_speech_backend()
        return selected or self._DEFAULT_BACKEND_OPTIONS[0][0]

    def _backend_id_for_selection(self, selection: int) -> str | None:
        if selection < 0 or selection >= len(self._speech_backend_options):
            return None
        return self._speech_backend_options[selection][0]

    def _get_available_voices(self) -> tuple[tuple[str, str], ...]:
        if self.controller is None or not hasattr(self.controller, "get_available_voices"):
            return ()
        return self.controller.get_available_voices() or ()

    def _get_selected_voice(self) -> str | None:
        if self.controller is None or not hasattr(self.controller, "get_selected_voice"):
            return None
        return self.controller.get_selected_voice()

    def _get_rate(self) -> int | None:
        if self.controller is None or not hasattr(self.controller, "get_rate"):
            return None
        return self.controller.get_rate()

    def _get_pitch(self) -> int | None:
        if self.controller is None or not hasattr(self.controller, "get_pitch"):
            return None
        return self.controller.get_pitch()

    def _get_volume(self) -> int | None:
        if self.controller is None or not hasattr(self.controller, "get_volume"):
            return None
        return self.controller.get_volume()

    def _voice_id_for_selection(self, selection: int) -> str | None:
        if selection < 0 or selection >= len(self._voice_options):
            return None
        return self._voice_options[selection][0]

    def _voice_selection_for_current_value(self) -> int:
        selected_voice = self._get_selected_voice()
        for index, (voice_id, _label) in enumerate(self._voice_options):
            if voice_id == selected_voice:
                return index
        return 0 if self._voice_options else -1

    @staticmethod
    def _stringify_optional_int(value: int | None) -> str:
        return "" if value is None else str(value)

    def _set_int_control_value(self, control, setter_name: str) -> None:
        if self.controller is None or not hasattr(self.controller, setter_name):
            return
        try:
            value = int(control.GetValue())
        except ValueError:
            return
        getattr(self.controller, setter_name)(value)
