class SpeechControlsMixin:
    _DEFAULT_BACKEND_OPTIONS = (
        ("nvda_controller", "NVDA Controller"),
        ("pyttsx3", "pyttsx3"),
    )

    def _build_speech_controls(self, panel, sizer, wx) -> None:
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
            self.speech_backend_choice,
            self.voice_choice,
            self.rate_ctrl,
            self.pitch_ctrl,
            self.volume_ctrl,
        ):
            sizer.Add(widget, 0, wx.EXPAND | wx.ALL, 4)

    def _bind_speech_control_events(self, wx) -> None:
        self.speech_backend_choice.Bind(wx.EVT_CHOICE, self._on_speech_backend_change)
        self.voice_choice.Bind(wx.EVT_CHOICE, self._on_voice_change)
        self.rate_ctrl.Bind(wx.EVT_TEXT, self._on_rate_change)
        self.pitch_ctrl.Bind(wx.EVT_TEXT, self._on_pitch_change)
        self.volume_ctrl.Bind(wx.EVT_TEXT, self._on_volume_change)

    def _on_speech_backend_change(self, _event):
        if self.controller is None or not hasattr(self.controller, "set_speech_backend"):
            return
        backend_id = self._backend_id_for_selection(self.speech_backend_choice.GetSelection())
        if backend_id is None:
            return
        try:
            self.controller.set_speech_backend(backend_id)
        except Exception as error:
            self._sync_speech_backend_choice()
            self._show_error(str(error), "Speech Backend Error")
            return
        self._sync_speech_backend_choice()
        self._sync_speech_controls()

    def _on_voice_change(self, _event):
        if self.controller is None or not hasattr(self.controller, "set_selected_voice"):
            return
        voice_id = self._voice_id_for_selection(self.voice_choice.GetSelection())
        if voice_id is not None:
            self.controller.set_selected_voice(voice_id)

    def _on_rate_change(self, _event):
        self._set_int_control_value(self.rate_ctrl, "set_rate")

    def _on_pitch_change(self, _event):
        self._set_int_control_value(self.pitch_ctrl, "set_pitch")

    def _on_volume_change(self, _event):
        self._set_int_control_value(self.volume_ctrl, "set_volume")

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
        self.voice_choice.Clear()
        for _voice_id, label in self._voice_options:
            self.voice_choice.Append(label)
        self.voice_choice.SetSelection(self._voice_selection_for_current_value())
        self.rate_ctrl.SetValue(self._stringify_optional_int(self._get_rate()))
        self.pitch_ctrl.SetValue(self._stringify_optional_int(self._get_pitch()))
        self.volume_ctrl.SetValue(self._stringify_optional_int(self._get_volume()))

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
