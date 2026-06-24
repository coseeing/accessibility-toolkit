class SpeechControlsMixin:
    _DEFAULT_ENGINE_OPTIONS = (
        ("NvdaController", "Nvda Controller"),
        ("Pyttsx3", "Pyttsx3"),
    )

    def _build_speech_controls(self, panel, sizer, wx) -> None:
        self._speech_engine_options = self._get_speech_engine_options()
        self.speech_engine_choice = wx.Choice(
            panel,
            choices=[label for _engine_id, label in self._speech_engine_options],
        )
        self._voice_options = self._get_available_voices()
        self.voice_choice = wx.Choice(
            panel,
            choices=[label for _voice_id, label in self._voice_options],
        )
        self.rate_slider = wx.Slider(panel, value=50, minValue=0, maxValue=100)
        self.pitch_slider = wx.Slider(panel, value=50, minValue=0, maxValue=100)
        self.volume_slider = wx.Slider(panel, value=50, minValue=0, maxValue=100)
        self.speech_backend_choice = self.speech_engine_choice
        self.rate_ctrl = self.rate_slider
        self.pitch_ctrl = self.pitch_slider
        self.volume_ctrl = self.volume_slider
        for widget in (
            self.speech_engine_choice,
            self.voice_choice,
            self.rate_slider,
            self.pitch_slider,
            self.volume_slider,
        ):
            sizer.Add(widget, 0, wx.EXPAND | wx.ALL, 4)

    def _bind_speech_control_events(self, wx) -> None:
        self.speech_engine_choice.Bind(wx.EVT_CHOICE, self._on_speech_engine_change)
        self.voice_choice.Bind(wx.EVT_CHOICE, self._on_voice_change)
        self.rate_slider.Bind(wx.EVT_SLIDER, self._on_rate_change)
        self.pitch_slider.Bind(wx.EVT_SLIDER, self._on_pitch_change)
        self.volume_slider.Bind(wx.EVT_SLIDER, self._on_volume_change)

    def _on_speech_engine_change(self, _event):
        if self.controller is None or not hasattr(self.controller, "set_speech_engine"):
            return
        engine_id = self._engine_id_for_selection(self.speech_engine_choice.GetSelection())
        if engine_id is None:
            return
        try:
            self.controller.set_speech_engine(engine_id)
        except Exception as error:
            self._sync_speech_engine_choice()
            self._show_error(str(error), "Speech Engine Error")
            return
        self._sync_speech_engine_choice()
        self._sync_speech_controls()

    def _on_speech_backend_change(self, event):
        self._on_speech_engine_change(event)

    def _on_voice_change(self, _event):
        if self.controller is None or not hasattr(self.controller, "set_selected_voice"):
            return
        if not self._voice_options:
            return
        voice_id = self._voice_id_for_selection(self.voice_choice.GetSelection())
        if voice_id is not None:
            self.controller.set_selected_voice(voice_id)

    def _on_rate_change(self, _event):
        self._set_slider_value(self.rate_slider, "set_rate", "rate")

    def _on_pitch_change(self, _event):
        self._set_slider_value(self.pitch_slider, "set_pitch", "pitch")

    def _on_volume_change(self, _event):
        self._set_slider_value(self.volume_slider, "set_volume", "volume")

    def _sync_speech_engine_choice(self) -> None:
        selected_engine = self._get_selected_speech_engine()
        for index, (engine_id, _label) in enumerate(self._speech_engine_options):
            if engine_id == selected_engine:
                self.speech_engine_choice.SetSelection(index)
                return
        if self._speech_engine_options:
            self.speech_engine_choice.SetSelection(0)

    def _sync_speech_backend_choice(self) -> None:
        self._sync_speech_engine_choice()

    def _sync_speech_controls(self) -> None:
        self._voice_options = self._get_available_voices()
        self.voice_choice.Clear()
        for _voice_id, label in self._voice_options:
            self.voice_choice.Append(label)
        if self._voice_options:
            self.voice_choice.Enable(True)
            self.voice_choice.SetSelection(self._voice_selection_for_current_value())
        else:
            self.voice_choice.Disable()
            self.voice_choice.SetSelection(-1)
        self._sync_numeric_slider(self.rate_slider, "rate", self._get_rate())
        self._sync_numeric_slider(self.pitch_slider, "pitch", self._get_pitch())
        self._sync_numeric_slider(self.volume_slider, "volume", self._get_volume())

    def _get_speech_engine_options(self) -> tuple[tuple[str, str], ...]:
        if self.controller is None or not hasattr(self.controller, "get_speech_engine_options"):
            return self._DEFAULT_ENGINE_OPTIONS
        options = self.controller.get_speech_engine_options()
        return options or self._DEFAULT_ENGINE_OPTIONS

    def _get_speech_backend_options(self) -> tuple[tuple[str, str], ...]:
        return self._get_speech_engine_options()

    def _get_selected_speech_engine(self) -> str:
        if self.controller is None or not hasattr(self.controller, "get_selected_speech_engine"):
            return self._DEFAULT_ENGINE_OPTIONS[0][0]
        selected = self.controller.get_selected_speech_engine()
        return selected or self._DEFAULT_ENGINE_OPTIONS[0][0]

    def _get_selected_speech_backend(self) -> str:
        return self._get_selected_speech_engine()

    def _engine_id_for_selection(self, selection: int) -> str | None:
        if selection < 0 or selection >= len(self._speech_engine_options):
            return None
        return self._speech_engine_options[selection][0]

    def _backend_id_for_selection(self, selection: int) -> str | None:
        return self._engine_id_for_selection(selection)

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

    def _get_supported_numeric_settings(self):
        if self.controller is None or not hasattr(self.controller, "get_supported_numeric_settings"):
            return ()
        return self.controller.get_supported_numeric_settings() or ()

    def _supported_numeric_setting_ids(self) -> set[str]:
        return {setting.id for setting in self._get_supported_numeric_settings()}

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

    def _sync_numeric_slider(self, slider, setting_id: str, value: int | None) -> None:
        settings = {setting.id: setting for setting in self._get_supported_numeric_settings()}
        setting = settings.get(setting_id)
        if setting is None:
            slider.SetValue(50)
            slider.Disable()
            return
        slider.SetLineSize(setting.step)
        slider.SetPageSize(setting.large_step)
        slider.SetValue(setting.default_percent if value is None else value)
        slider.Enable(True)

    def _set_slider_value(self, slider, setter_name: str, setting_id: str) -> None:
        if self.controller is None or not hasattr(self.controller, setter_name):
            return
        if setting_id not in self._supported_numeric_setting_ids():
            return
        getattr(self.controller, setter_name)(slider.GetValue())
