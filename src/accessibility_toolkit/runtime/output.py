import logging
from collections.abc import Callable
from dataclasses import dataclass

from accessibility_toolkit.output import Capabilities, QueuedService, ToneOutput, WaveOutput
from accessibility_toolkit.output.speech import SpeechEngineOption, SpeechService
from accessibility_toolkit.scheduling import Scheduler

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OutputServices:
    scheduler: Scheduler
    speech: SpeechService
    speaker: QueuedService
    capabilities: Capabilities


def build_output_services(
    *,
    engine_options_factory: Callable[[Scheduler], tuple[SpeechEngineOption, ...]],
    selected_engine_id: str,
    fallback_engine_id: str | None = None,
    tone_output: ToneOutput | None = None,
    wave_output: WaveOutput | None = None,
    on_engine_fallback: Callable[[str], None] | None = None,
) -> OutputServices:
    if selected_engine_id is None:
        raise TypeError("selected speech engine id is required")
    scheduler = Scheduler()
    try:
        engine_options = engine_options_factory(scheduler)
        try:
            speech = SpeechService(
                engine_options=engine_options,
                selected_engine_id=selected_engine_id,
                scheduler=scheduler,
            )
        except ValueError:
            fallback_id = fallback_engine_id or selected_engine_id
            _logger.warning(
                "Unknown configured speech engine %r; falling back to %s",
                selected_engine_id,
                fallback_id,
            )
            speech = SpeechService(
                engine_options=engine_options,
                selected_engine_id=fallback_id,
                scheduler=scheduler,
            )
            if on_engine_fallback is not None:
                on_engine_fallback(fallback_id)
        speaker = QueuedService(speech=speech)
        return OutputServices(
            scheduler=scheduler,
            speech=speech,
            speaker=speaker,
            capabilities=Capabilities(
                speech=speaker,
                tone=tone_output,
                wave=wave_output,
            ),
        )
    except Exception:
        scheduler.shutdown()
        raise
