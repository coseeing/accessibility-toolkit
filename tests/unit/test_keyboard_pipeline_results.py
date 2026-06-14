from application.input.results import AppKeyEventResult, KeyboardPipelineResult


def test_keyboard_pipeline_result_preserves_both_dimensions():
    result = KeyboardPipelineResult(
        send_to_system=True,
        app_result=AppKeyEventResult.HANDLED_CONTINUE,
    )

    assert result.send_to_system is True
    assert result.app_result is AppKeyEventResult.HANDLED_CONTINUE
