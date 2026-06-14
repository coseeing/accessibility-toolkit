# Task 0 Review

## Scope

- Completion report: `docs/superpowers/finish_task0.md`
- Spec: `docs/superpowers/specs/2026-06-13-output-sequential-parallel-mode-design.md`
- Plan: `docs/superpowers/plans/2026-06-13-output-sequential-parallel-mode-implementation.md`
- Reviewed commits in chronological order:
  - `e340ec1` `docs: add output sequential/parallel mode design spec`
  - `df78efe` `docs: add zh-TW translation of output sequential/parallel mode design`
  - `47fcb86` `docs: clarify PARALLEL mode behavior with only speech output`
  - `af90446` `docs: add output sequential/parallel mode implementation plan`
  - `336dafe` `test: add output mode sequential/parallel tests`
  - `c5bc34d` `feat: add OutputMode SEQUENTIAL/PARALLEL to QueuedOutputService`

## Findings

### 1. Medium: `SEQUENTIAL` mode correctness depends on an external NVDA controller contract that is not recorded or verified in this repo

- Spec and plan claim that sequential mode guarantees ordered execution of consecutive `speak()` calls, and the design diagram explicitly says the second call runs after the first completes. See `docs/superpowers/specs/2026-06-13-output-sequential-parallel-mode-design.md:24`, `:53`, `:101`, `:116`.
- The implementation in `QueuedOutputService.speak()` only serializes calls to `SpeechService.speak()` through `_shared_scheduler`; it does not itself wait for backend completion before dequeuing the next top-level speak. See `src/application/output_service.py:46-49`.
- Whether this still yields true non-overlapping playback depends on the behavior of the NVDA controller API call used by `NvdaControllerSpeechOutput`. The repo code does not document that dependency or prove it with tests. See `src/adapters/windows/nvda_controller.py:77-99`.
- If the underlying `nvdaController_speakSsml(...)` call is used in blocking/synchronous mode, then sequential playback may still be correct in practice. If not, the guarantee is overstated. The problem is that this contract lives outside the repo and is currently implicit.

Recommendation:
- Record the relied-upon NVDA controller behavior in code comments and/or design docs.
- Add a backend-level test or integration note that makes it explicit that `SEQUENTIAL` depends on the NVDA path operating in blocking/FIFO-safe mode.

### 2. Medium: the new tests only validate a synchronous fake backend, so they miss the real scheduler interaction the feature depends on

- `test_sequential_orders_consecutive_speak_calls()` and related tests use `FakeSpeechOutput`, whose `speak()` implementation just appends to a list synchronously. See `tests/unit/test_output_service.py:7-19`, `:155-167`.
- The test then waits on a sentinel scheduled into `_shared_scheduler`, which only proves the top-level queue drained; it does not prove backend playback completed. See `tests/unit/test_output_service.py:164-166`.
- Because the tests never exercise the real NVDA-backed contract, they cannot prove the sequential guarantee that the design advertises. This leaves the implementation looking green while a critical external assumption remains unverified inside the repo.

Recommendation:
- Add a regression test with a scheduler-backed fake backend that returns before playback is finished, matching the current `nvda_controller` behavior more closely.
- Keep the current unit tests, but add at least one backend-behavior test that fails unless sequential mode waits for actual playback completion.

## Commit Review Notes

### `e340ec1` design spec

- Clear problem statement and API direction.
- Main gap is that the document states a strong guarantee without documenting the external NVDA controller behavior it relies on.

### `df78efe` zh-TW translation

- Translation stays aligned with the English spec.
- It inherits the same undocumented external contract assumption.

### `47fcb86` PARALLEL clarification

- Good clarification that "parallel" is not observable yet with only speech output.
- Does not resolve the separate `SEQUENTIAL` contract problem.

### `af90446` implementation plan

- The plan follows the spec closely.
- The test strategy is too optimistic because it validates only a synchronous fake output, not the real backend contract the feature depends on.

### `336dafe` test commit

- Tests are readable and capture the intended API.
- Coverage is insufficient for the backend completion semantics the design relies on.

### `c5bc34d` implementation commit

- The API surface is small and the lifecycle wiring is straightforward.
- The shared scheduler serializes top-level dispatch correctly, but the end-to-end sequential guarantee depends on backend behavior that should be made explicit.

## Validation

Commands run:

```bash
pytest tests/unit/test_output_service.py -v
pytest tests/unit/test_output_service.py tests/unit/test_key_echo_app_service.py tests/unit/test_app_wx.py -v
```

Observed results:

- `tests/unit/test_output_service.py`: 10 passed
- targeted compatibility suite: 60 passed

Residual risk noted during review:

- The repo-level tests do not prove the NVDA controller path is operating in the blocking/FIFO-safe way that `SEQUENTIAL` mode assumes.
