from application.input.keyboard_pipeline import assemble_pipeline_result
from application.input.results import AppKeyEventResult, KeyboardPipelineResult


def test_assemble_pipeline_result_keeps_send_to_system_and_app_result():
    result = assemble_pipeline_result(
        send_to_system=True,
        app_result=AppKeyEventResult.HANDLED_CONTINUE,
    )

    assert result == KeyboardPipelineResult(
        send_to_system=True,
        app_result=AppKeyEventResult.HANDLED_CONTINUE,
    )
