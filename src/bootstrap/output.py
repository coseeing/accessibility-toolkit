import logging
from collections.abc import Callable
from dataclasses import dataclass

from adapters.outputs.interfaces import ToneOutput
from application.output import Capabilities, QueuedService, Scheduler
from application.output.speech import SpeechBackendOption, SpeechService

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OutputServices:
    scheduler: Scheduler
    speech: SpeechService
    speaker: QueuedService
    capabilities: Capabilities


def build_output_services(
    *,
    backend_options_factory: Callable[[Scheduler], tuple[SpeechBackendOption, ...]],
    selected_backend_id: str,
    fallback_backend_id: str | None = None,
    tone_output: ToneOutput | None = None,
    on_backend_fallback: Callable[[str], None] | None = None,
) -> OutputServices:
    scheduler = Scheduler()
    backend_options = backend_options_factory(scheduler)
    try:
        speech = SpeechService(
            backend_options=backend_options,
            selected_backend_id=selected_backend_id,
            scheduler=scheduler,
        )
    except ValueError:
        fallback_id = fallback_backend_id or selected_backend_id
        _logger.warning(
            "Unknown configured speech backend %r; falling back to %s",
            selected_backend_id,
            fallback_id,
        )
        speech = SpeechService(
            backend_options=backend_options,
            selected_backend_id=fallback_id,
            scheduler=scheduler,
        )
        if on_backend_fallback is not None:
            on_backend_fallback(fallback_id)
    speaker = QueuedService(speech=speech)
    return OutputServices(
        scheduler=scheduler,
        speech=speech,
        speaker=speaker,
        capabilities=Capabilities(speech=speaker, tone=tone_output),
    )
