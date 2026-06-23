# Runtime Providers And Typed Events Finish Report

Date: 2026-06-23

## Summary

Implemented the runtime provider extraction and typed event boundary plan in the
`runtime-providers-typed-events` worktree.

Milestone 1 extracts shared runtime wiring into bootstrap helpers:

- `PlatformProvider` and `PlatformServices` wrap existing platform factories.
- `build_output_services()` centralizes scheduler, speech, speaker, and
  capability assembly.
- `build_app_runtime_parts()` centralizes common input, hotkey, clipboard,
  tone, and output wiring with opt-in clipboard and tone construction.
- Key Echo, Access8Graph, and NVDA Remote entrypoints now use the shared
  runtime builders.

Milestone 2 replaces dict-first app/UI status flow with typed events:

- Shared runtime events live in `src/application/events.py`.
- App-domain events live under each app package.
- Mode manager, app services, app use cases, and UI frames use typed event
  dataclasses as the primary listener contract.
- NVDA Remote keeps protocol/router dict payloads isolated and converts them at
  the app boundary.
- Transitional `StatusEvent.from_payload()` remains only as a conversion helper.

## Review Gates

- M1 spec compliance review: passed.
- M1 code quality review: approved after resource ownership fixes.
- M2 spec compliance review: passed after NVDA Remote boundary fixes.
- M2 code quality review: approved after event coercion and listener type fixes.

## Validation

- Baseline after restoring ignored local Access8Graph fixture:
  `pytest tests/unit tests/integration -v` -> `473 passed`.
- M1 focused verification:
  `pytest tests/unit/test_bootstrap_platform.py tests/unit/test_bootstrap_output.py tests/unit/test_bootstrap_app_runtime.py tests/unit/test_key_echo_app_service.py tests/unit/test_access8graph_app_service.py tests/unit/test_nvda_remote_app_service.py tests/unit/test_app_wx.py -v` -> `114 passed`.
- M2 focused verification:
  `pytest tests/unit/test_application_events.py tests/unit/test_app_events.py tests/unit/test_mode_manager.py tests/unit/test_key_echo_use_cases.py tests/unit/test_key_echo_app_service.py tests/unit/test_access8graph_app_service.py tests/unit/test_nvda_remote_use_cases.py tests/unit/test_nvda_remote_app_service.py tests/unit/test_app_wx.py tests/unit/test_access8graph_ui.py -v` -> `131 passed`.
- Final verification:
  `pytest tests/unit tests/integration -v` -> `500 passed`.
- Whitespace check:
  `git diff --check` -> no output.

## New Commit List

- `ee554d6` test: cover bootstrap platform provider
- `b4865cb` refactor: add runtime output builder
- `435e7f7` refactor: centralize app runtime wiring
- `f041e00` refactor: use shared runtime builder in key echo
- `948a996` refactor: use shared runtime builder in access8graph
- `0495a17` refactor: use shared runtime builder in nvda remote
- `23a6de8` refactor: tighten runtime builder resource ownership
- `60af804` feat: add typed application events
- `af8aea3` feat: add app typed events
- `bde2331` refactor: emit typed mode events
- `8ed87d9` refactor: migrate key echo typed events
- `573e1c2` refactor: migrate access8graph typed events
- `53a0798` refactor: migrate nvda remote typed events
- `c335050` refactor: migrate UI status consumers to typed events
- `a108ee1` refactor: remove dict-first app status flow
- `291073f` refactor: keep nvda remote status boundary typed
- `8cb9126` refactor: tighten typed status event boundaries

## Notes

- `Access8Graph/tests/test.graphml` is ignored by git but required for the full
  test suite. It was copied from the original checkout into the worktree for
  local verification and was not committed.
- Remaining raw dict status assertions are protocol/message-router tests, not
  app/UI listener contracts.
