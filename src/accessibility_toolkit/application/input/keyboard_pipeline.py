from accessibility_toolkit.application.input.results import AppKeyEventResult, KeyboardPipelineResult


def assemble_pipeline_result(
    *,
    send_to_system: bool,
    app_result: AppKeyEventResult,
) -> KeyboardPipelineResult:
    return KeyboardPipelineResult(
        send_to_system=send_to_system,
        app_result=app_result,
    )
