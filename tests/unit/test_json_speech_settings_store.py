from __future__ import annotations

import json

from adapters.config.json_speech_settings import JsonSpeechSettingsStore


def test_missing_file_returns_defaults(tmp_path):
    store = JsonSpeechSettingsStore(tmp_path / "settings.json")

    assert store.load_engine_id(default_engine_id="Pyttsx3") == "Pyttsx3"
    assert store.load_voice("Pyttsx3") is None
    assert store.load_numeric_setting("Pyttsx3", "rate") is None


def test_malformed_file_returns_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{bad", encoding="utf-8")
    store = JsonSpeechSettingsStore(path)

    assert store.load_engine_id(default_engine_id="NVDA") == "NVDA"


def test_store_preserves_schema_and_unrelated_keys(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"other": {"enabled": True}}), encoding="utf-8")
    store = JsonSpeechSettingsStore(path)

    store.save_engine_id("Pyttsx3")
    store.save_voice("Pyttsx3", "voice-1")
    store.save_numeric_setting("Pyttsx3", "rate", 140)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload == {
        "other": {"enabled": True},
        "speech_engine": "Pyttsx3",
        "speech_engines": {
            "Pyttsx3": {
                "voice": "voice-1",
                "rate": 100,
            }
        },
    }
