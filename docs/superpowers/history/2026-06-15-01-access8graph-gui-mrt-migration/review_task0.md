# Access8Graph GUI MRT Migration Review - Task 0

Review date: 2026-06-15

## Review Scope

Reviewed source documents:

- `docs/superpowers/finish_task0.md`
- `docs/superpowers/specs/2026-06-15-access8graph-gui-mrt-migration-design.md`
- `docs/superpowers/plans/2026-06-15-access8graph-gui-mrt-migration-implementation.md`

Reviewed commits, ordered from oldest to newest as requested:

1. `4163258 feat: migrate access8graph graphml core`
2. `d4054bf feat: add access8graph key translator`
3. `adea131 feat: add access8graph flow output adapter`
4. `dcafe77 feat: port access8graph mrt flow`
5. `db51504 test: cover access8graph mrt flow smoke path`
6. `f8c7c8e feat: add access8graph app service`
7. `1a6de69 feat: add access8graph gui runtime`
8. `82f981e fix: correct datas variable name in transfer_display`

## Findings

### Critical: invalid GraphML can enter active navigation instead of failing before keyboard capture

References:

- `src/apps/access8graph/graphml/model.py:305`
- `src/apps/access8graph/graphml/model.py:310`
- `src/apps/access8graph/service.py:117`
- `src/apps/access8graph/service.py:134`

`Graph.load()` catches `BaseException`, prints the exception, and returns without failing. This leaves an empty `Graph` object that `MrtModel` and `MrtFlow` can still receive. `Access8GraphAppService.start_navigation()` then delegates to `ModeManager.activate_mode()` without checking a failure value, and `_start_flow()` sets `_navigation_running = True` before graph parsing/model construction is proven valid.

This violates the design requirement that parser/model construction failure should show an error and leave keyboard capture inactive. In the current lifecycle, active keyboard capture is started before `_start_flow()` parses the selected file, so a malformed file can leave the app in navigation mode with keyboard capture active, hotkey capture stopped, and a useless or empty flow.

Manual reproduction performed during review:

```text
PYTHONPATH=src python <script using Access8GraphAppService with malformed /tmp/bad-access8graph.graphml>
no element found: line 1, column 13
running True input True hotkey False active_mode navigation flow <apps.access8graph.flow.MrtFlow object ...>
```

Recommended fix:

- Make malformed XML or invalid GraphML fail explicitly instead of being swallowed in `Graph.load()`.
- Validate/build `Graph`, `MrtModel`, and `MrtFlow` before activating keyboard capture, or add rollback around `mode.enter()` failures.
- Set `_navigation_running = True` only after flow construction and startup speech succeed enough for a valid active state.
- Add regression tests asserting malformed `.graphml` does not leave `input_capture.running == True`, does not stop hotkey capture permanently, and does not create a running flow.

### High: selected file validation is incomplete and can defer missing-file failures until after activation

References:

- `src/apps/access8graph/service.py:109`
- `src/apps/access8graph/service.py:111`
- `src/apps/access8graph/service.py:117`

`choose_graphml()` only checks `Path(path).suffix != ".graphml"` and stores the path. It does not verify the file exists, and the suffix check is case-sensitive. The implementation plan expected selection to store a path only when it exists and has a `.graphml` suffix. The GUI file picker normally returns an existing file, but the service API can still receive a missing path, or the selected file can be deleted before `start_navigation()`.

Because actual loading happens inside `_start_flow()` after `ModeManager.activate_mode()` begins activation, missing-file errors can occur after hotkey capture has been stopped and keyboard capture has started. This is the same lifecycle risk as the malformed-file case, but it can happen with a previously valid user selection.

Recommended fix:

- Normalize suffix with `.suffix.lower()`.
- Check `Path(path).is_file()` in `choose_graphml()`.
- Revalidate existence immediately before start, before keyboard capture activation.
- Add tests for missing file, uppercase `.GRAPHML` if intended to be accepted, and deleted-after-selection behavior.

### Medium: UI error status can be overwritten immediately by normal sync text

References:

- `src/ui/access8graph/main_frame.py:87`
- `src/ui/access8graph/main_frame.py:90`
- `src/apps/access8graph/service.py:117`

`Access8GraphMainFrame._on_controller_status()` sets `status_label` to the error message when `kind == "error"`, but then always calls `_sync_controls()`. `_sync_controls()` rewrites the same label to either `Navigation running`, the selected file name, or `No file selected`. As a result, lifecycle errors reported through the controller status callback can disappear immediately.

This conflicts with the spec requirement that loading or starting failures show concise error text. It also makes activation failures harder to recover from because `start_navigation()` ignores the `activate_mode()` return value, so the button handler may not show a message box for failures that are only reported through status.

Recommended fix:

- Preserve error status in `_on_controller_status()` by returning after setting the error label, or keep a last-error state that `_sync_controls()` respects.
- Make `start_navigation()` raise or otherwise return a failure result when `activate_mode()` returns `False`.
- Add a UI unit test where the fake controller emits an error status and assert the label still contains the error after the handler finishes.

## Commit-Order Review Notes

### `4163258 feat: migrate access8graph graphml core`

The GraphML core was moved into `src/apps/access8graph/graphml/` and basic import/model smoke coverage was added. The main issue introduced here is error handling: parse failures are swallowed with `print(e)` and `return`, which is unsafe once this code is attached to active keyboard capture.

The later `82f981e` fix for `datas` naming addresses one concrete porting bug, but the broader parser failure contract remains unresolved.

### `d4054bf feat: add access8graph key translator`

The HID-to-command translation follows the approved first-phase scope: arrow keys, Enter, Escape, Home/End, and MRT command letters. Key-up and unsupported keys are ignored by the translator, which matches the intended command-level behavior.

No blocking issue found in this commit.

### `adea131 feat: add access8graph flow output adapter`

The output adapter correctly maps text lists to speech sequences and includes `BreakCommand` between items, matching the updated spec decision to use this project native speech sequence pause command.

No blocking issue found in this commit.

### `dcafe77 feat: port access8graph mrt flow`

The flow port is structurally aligned with the original state-machine approach and keeps graph navigation logic mostly independent from NVDA. Existing tests cover startup, menu movement, and unsupported command behavior.

Residual risk: coverage is still mostly smoke-level for actual MRT navigation paths, route planning, and branch edge cases.

### `db51504 test: cover access8graph mrt flow smoke path`

The integration smoke test verifies a fixture can start the flow and accept menu navigation. This is useful, but it does not exercise malformed input, missing files, or lifecycle rollback after partial activation.

The critical lifecycle issues above are therefore not covered by the current integration test.

### `f8c7c8e feat: add access8graph app service`

This commit wires selection, mode activation, keyboard pipeline handling, and speech settings. The main problems are concentrated here: file validation is too shallow, `start_navigation()` ignores activation failure, and graph/model creation happens inside mode entry after keyboard activation begins.

This is the highest-priority area to fix before considering the migration production-ready.

### `1a6de69 feat: add access8graph gui runtime`

The GUI follows the key_echo shell pattern and exposes main, speech settings, and exit behavior through the shared tray shell. The selected-file and start/stop controls are covered by basic tests.

The main UI issue is error status handling: controller error messages can be overwritten by `_sync_controls()` in the same callback.

### `82f981e fix: correct datas variable name in transfer_display`

The targeted fix addresses a concrete typo in the ported navigator path. No additional issue found in this commit.

## Verification Performed

Commands run:

```text
pytest tests/unit/test_access8graph_*.py tests/integration/test_access8graph_mrt_flow.py -v
pytest tests/unit tests/integration -v
```

Results:

- Access8Graph focused tests: `42 passed`
- Full suite: `420 passed`

Additional manual check:

- Malformed `.graphml` start path reproduced the critical lifecycle bug: service reported navigation running while input capture was active and hotkey capture was stopped.

## Review Conclusion

The first-phase MRT GUI migration is close structurally, and the happy path has passing automated coverage. However, the current implementation should not be treated as complete because invalid or missing graph files can cross the boundary into active keyboard capture. That is the highest-risk failure mode for an accessibility tool because it can intercept user keyboard input while the navigation state is invalid.

Fix the graph loading validation and activation rollback first, then add regression coverage around malformed files, missing files, and UI error persistence.
