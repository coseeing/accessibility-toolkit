import logging
from collections.abc import Callable
from dataclasses import dataclass

from adapters.outputs.interfaces import ToneOutput
from application.output import Capabilities, QueuedService, Scheduler
from application.output.speech import SpeechEngineOption, SpeechService

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OutputServices:
    scheduler: Scheduler
    speech: SpeechService
    speaker: QueuedService
    capabilities: Capabilities


def build_output_services(
    *,
    engine_options_factory: Callable[[Scheduler], tuple[SpeechEngineOption, ...]] | None = None,
    selected_engine_id: str | None = None,
    fallback_engine_id: str | None = None,
    backend_options_factory: Callable[[Scheduler], tuple[SpeechEngineOption, ...]] | None = None,
    selected_backend_id: str | None = None,
    fallback_backend_id: str | None = None,
    tone_output: ToneOutput | None = None,
    on_engine_fallback: Callable[[str], None] | None = None,
    on_backend_fallback: Callable[[str], None] | None = None,
) -> OutputServices:
    resolved_options_factory = engine_options_factory or backend_options_factory
    resolved_selected_engine_id = selected_engine_id or selected_backend_id
    resolved_fallback_engine_id = fallback_engine_id or fallback_backend_id
    resolved_on_engine_fallback = on_engine_fallback or on_backend_fallback
    if resolved_options_factory is None or resolved_selected_engine_id is None:
        raise TypeError("speech engine factory and selected engine id are required")
    scheduler = Scheduler()
    try:
        engine_options = resolved_options_factory(scheduler)
        try:
            speech = SpeechService(
                engine_options=engine_options,
                selected_engine_id=resolved_selected_engine_id,
                scheduler=scheduler,
            )
        except ValueError:
            fallback_id = resolved_fallback_engine_id or resolved_selected_engine_id
            _logger.warning(
                "Unknown configured speech engine %r; falling back to %s",
                resolved_selected_engine_id,
                fallback_id,
            )
            speech = SpeechService(
                engine_options=engine_options,
                selected_engine_id=fallback_id,
                scheduler=scheduler,
            )
            if resolved_on_engine_fallback is not None:
                resolved_on_engine_fallback(fallback_id)
        speaker = QueuedService(speech=speech)
        return OutputServices(
            scheduler=scheduler,
            speech=speech,
            speaker=speaker,
            capabilities=Capabilities(speech=speaker, tone=tone_output),
        )
    except Exception:
        scheduler.shutdown()
        raise
