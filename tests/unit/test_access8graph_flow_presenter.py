import pytest

from apps.access8graph.navigation.model import (
    NavigationStateId,
    PresentationEffects,
    TransitionOutcome,
    TransitionResult,
)


class RecordingOutput:
    """Output port spy that captures all calls for test assertions."""

    def __init__(self):
        self.calls: list[tuple] = []

    def cancel(self):
        self.calls.append(("cancel",))

    def speak(self, items):
        self.calls.append(("speak", tuple(items)))

    def beep(self):
        self.calls.append(("beep",))


# ---------------------------------------------------------------------------
# Step 1: basic ordering -- TRANSITIONED
# ---------------------------------------------------------------------------


def test_presenter_orders_effects_and_speaks_once():
    output = RecordingOutput()
    from apps.access8graph.navigation.presenter import FlowPresenter

    presenter = FlowPresenter(output)
    effects = PresentationEffects(
        close_messages=("old closed",),
        open_messages=("new opened",),
        hints=("hint",),
        view_items=("label", "1 of 2"),
    )

    presenter.present(
        TransitionResult.transitioned(
            source=NavigationStateId.MODE,
            target=NavigationStateId.LINES,
            effects=effects,
        )
    )

    assert output.calls == [
        ("cancel",),
        ("speak", ("old closed", "new opened", "hint", "label", "1 of 2")),
    ]


def test_presenter_transitioned_empty_effects_no_output():
    output = RecordingOutput()
    from apps.access8graph.navigation.presenter import FlowPresenter

    presenter = FlowPresenter(output)

    presenter.present(
        TransitionResult.transitioned(
            source=NavigationStateId.MODE,
            target=NavigationStateId.LINES,
            effects=PresentationEffects(),
        )
    )

    assert output.calls == []


def test_presenter_handled_orders_effects_like_transitioned():
    output = RecordingOutput()
    from apps.access8graph.navigation.presenter import FlowPresenter

    presenter = FlowPresenter(output)
    effects = PresentationEffects(
        close_messages=("closed",),
        open_messages=("opened",),
        hints=("hint",),
        view_items=("view",),
    )

    presenter.present(
        TransitionResult.handled(
            source=NavigationStateId.MODE,
            effects=effects,
        )
    )

    assert output.calls == [
        ("cancel",),
        ("speak", ("closed", "opened", "hint", "view")),
    ]


# ---------------------------------------------------------------------------
# Step 2: REJECTED
# ---------------------------------------------------------------------------


def test_presenter_rejected_beeps_and_speaks_current_view():
    output = RecordingOutput()
    from apps.access8graph.navigation.presenter import FlowPresenter

    presenter = FlowPresenter(output)
    effects = PresentationEffects(
        view_items=("current label", "current detail"),
    )

    presenter.present(
        TransitionResult.rejected(
            source=NavigationStateId.MODE,
            effects=effects,
        )
    )

    assert output.calls == [
        ("beep",),
        ("speak", ("current label", "current detail")),
    ]


def test_presenter_rejected_empty_view_still_beeps():
    output = RecordingOutput()
    from apps.access8graph.navigation.presenter import FlowPresenter

    presenter = FlowPresenter(output)

    presenter.present(
        TransitionResult.rejected(
            source=NavigationStateId.MODE,
        )
    )

    assert output.calls == [
        ("beep",),
    ]


# ---------------------------------------------------------------------------
# Step 3: UNHANDLED
# ---------------------------------------------------------------------------


def test_presenter_unhandled_no_output():
    output = RecordingOutput()
    from apps.access8graph.navigation.presenter import FlowPresenter

    presenter = FlowPresenter(output)

    presenter.present(
        TransitionResult(
            outcome=TransitionOutcome.UNHANDLED,
            source=NavigationStateId.MODE,
            target=NavigationStateId.MODE,
            effects=PresentationEffects(
                view_items=("should not appear",),
            ),
        )
    )

    assert output.calls == []


# ---------------------------------------------------------------------------
# Step 4: cancel is called before speak
# ---------------------------------------------------------------------------


def test_presenter_cancel_before_speak():
    """Cancel must be called before speak, never after."""
    output = RecordingOutput()
    from apps.access8graph.navigation.presenter import FlowPresenter

    presenter = FlowPresenter(output)
    effects = PresentationEffects(
        view_items=("item",),
    )

    presenter.present(
        TransitionResult.transitioned(
            source=NavigationStateId.MODE,
            target=NavigationStateId.LINES,
            effects=effects,
        )
    )

    cancel_idx = next(
        i for i, (name, *_) in enumerate(output.calls) if name == "cancel"
    )
    speak_idx = next(
        i for i, (name, *_) in enumerate(output.calls) if name == "speak"
    )
    assert cancel_idx < speak_idx


# ---------------------------------------------------------------------------
# Step 5: non-empty filtering
# ---------------------------------------------------------------------------


def test_presenter_filters_empty_items():
    output = RecordingOutput()
    from apps.access8graph.navigation.presenter import FlowPresenter

    presenter = FlowPresenter(output)
    effects = PresentationEffects(
        close_messages=("close", "", None),
        open_messages=("open",),
        hints=(),
        view_items=("view",),
    )

    presenter.present(
        TransitionResult.transitioned(
            source=NavigationStateId.MODE,
            target=NavigationStateId.LINES,
            effects=effects,
        )
    )

    assert output.calls == [
        ("cancel",),
        ("speak", ("close", "open", "view")),
    ]


# ---------------------------------------------------------------------------
# Step 6: exception resilience
# ---------------------------------------------------------------------------


def test_presenter_propagates_exceptions_to_app_boundary():
    """Exceptions during presentation propagate to the caller (app-service boundary)."""
    output = RecordingOutput()
    from apps.access8graph.navigation.presenter import FlowPresenter

    presenter = FlowPresenter(output)

    class BrokenEffects:
        @property
        def close_messages(self):
            raise RuntimeError("output adapter failure")

    result = TransitionResult(
        outcome=TransitionOutcome.TRANSITIONED,
        source=NavigationStateId.MODE,
        target=NavigationStateId.LINES,
        effects=BrokenEffects(),
    )

    with pytest.raises(RuntimeError, match="output adapter failure"):
        presenter.present(result)

    assert output.calls == []
