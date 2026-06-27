from __future__ import annotations

import pytest

from tests.unit.access8graph_flow_scenarios import (
    FLOW_SCENARIOS,
    LEGACY_STATE_IDS,
    FlowScenario,
    FlowTrace,
    capture_legacy_trace,
)


# ---------------------------------------------------------------------------
# Manifest coverage tests
# ---------------------------------------------------------------------------

def test_characterization_scenarios_cover_every_legacy_state() -> None:
    covered = {scenario.start_state for scenario in FLOW_SCENARIOS}
    assert covered == LEGACY_STATE_IDS, (
        f"Missing states: {LEGACY_STATE_IDS - covered}, "
        f"Extra states: {covered - LEGACY_STATE_IDS}"
    )


def test_every_legacy_state_has_success_rejection_and_exit_coverage() -> None:
    for state_id in LEGACY_STATE_IDS:
        state_scenarios = [
            scenario for scenario in FLOW_SCENARIOS
            if scenario.start_state == state_id
        ]
        assert state_scenarios, f"No scenarios for state {state_id}"
        assert any(
            item.expected_success for item in state_scenarios
        ), f"No success scenario for {state_id}"
        assert any(
            not item.expected_success for item in state_scenarios
        ), f"No rejection scenario for {state_id}"
        assert any(
            item.expected_state != state_id for item in state_scenarios
        ), f"No exit scenario for {state_id}"


# ---------------------------------------------------------------------------
# Parameterized scenario execution
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("scenario", FLOW_SCENARIOS, ids=lambda s: s.id)
def test_scenario(scenario: FlowScenario) -> None:
    trace: FlowTrace = capture_legacy_trace(scenario)

    # Verify expected state
    assert trace.state_id == scenario.expected_state, (
        f"Expected state '{scenario.expected_state}', "
        f"got '{trace.state_id}' for scenario '{scenario.id}'"
    )

    # Verify success/failure (beep tracks rejection)
    success = all(call.kind != "beep_failure" for call in trace.output_calls)
    assert success == scenario.expected_success, (
        f"Expected success={scenario.expected_success}, "
        f"got success={success} (beeps present={not success}) "
        f"for scenario '{scenario.id}'"
    )

    # Verify explicit beep flag when set
    if scenario.expected_beep:
        has_beep = any(call.kind == "beep_failure" for call in trace.output_calls)
        assert has_beep, (
            f"Expected beep for scenario '{scenario.id}' but none found"
        )

    # Auto-select (empty-command) scenarios transition during arrange
    # without _speak_current_view being called; they legitimately have no output.
    if scenario.command:
        assert len(trace.output_calls) > 0, (
            f"Scenario '{scenario.id}' produced no output calls"
        )
