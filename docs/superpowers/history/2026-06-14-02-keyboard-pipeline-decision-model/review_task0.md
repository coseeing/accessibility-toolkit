# Review Task 0

## Findings

### 1. Hotkey paths now report `UNHANDLED` even when they actively handle and suppress the event

**Severity:** Medium

The new model’s stated purpose is to preserve app-internal semantics in `KeyboardPipelineResult.app_result`, not just the final pass-through bit. However, both hotkey paths currently return `UNHANDLED` after they have clearly handled the event and chosen suppression:

- Windows keypress hotkey capture invokes the handler, suppresses the event, but returns `UNHANDLED`
  - [src/adapters/windows/hotkey.py](/workspace/nvda-remote-client/src/adapters/windows/hotkey.py:175)
  - [src/adapters/windows/hotkey.py](/workspace/nvda-remote-client/src/adapters/windows/hotkey.py:177)
- macOS event tap invokes the hotkey handler, suppresses the event, but returns `UNHANDLED`
  - [src/adapters/macos/event_tap.py](/workspace/nvda-remote-client/src/adapters/macos/event_tap.py:135)
  - [src/adapters/macos/event_tap.py](/workspace/nvda-remote-client/src/adapters/macos/event_tap.py:138)

This does not break suppression today because adapters only consult `send_to_system`, but it breaks the semantic contract of `app_result`. Any logging, diagnostics, or future pipeline logic reading `app_result` will be told that the event was not handled when it actually was.

## Spec Alignment Note

The original review found that `nvda_remote` had adopted Windows `Num Lock` pass-through behavior ahead of the spec text. The spec has since been updated to match the implemented behavior, so that discrepancy is no longer an active review finding.

Current accepted behavior:

- in `nvda_remote`, Windows `Num Lock` is passed through to the local system
- `Num Lock` does not flow into remote forwarding in this phase

## Reviewed Commits

Reviewed in chronological order, as listed in `finish_task0.md`:

1. `8cda556` `feat: add keyboard pipeline result types`
2. `5515522` `feat: add keyboard pipeline assembly helper`
3. `584a192` `refactor: return app key event results from policies`
4. `354d6c5` `refactor: return app results from key echo input use case`
5. `2fe4a84` `refactor: switch keyboard captures to pipeline result`
6. `62b0a56` `feat: add key echo keyboard pipeline`
7. `4b4fa85` `refactor: adapt nvda remote service to pipeline result`
8. `5cd88c4` `test: verify keyboard pipeline decision model refactor`

## Verification

I compared the implementation against:

- [2026-06-14-keyboard-pipeline-decision-model-design.md](/workspace/nvda-remote-client/docs/superpowers/specs/2026-06-14-keyboard-pipeline-decision-model-design.md:1)
- [2026-06-14-keyboard-pipeline-decision-model-implementation.md](/workspace/nvda-remote-client/docs/superpowers/plans/2026-06-14-keyboard-pipeline-decision-model-implementation.md:1)

I also ran:

```bash
pytest tests/unit -q
```

Result:

```text
373 passed in 1.19s
```
