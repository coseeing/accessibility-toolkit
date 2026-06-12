# Special Keys and JIS HID Expansion Design

## Summary

This design extends the existing HID-first keyboard model to cover the special keys and JIS-specific keys that were intentionally excluded from the previous `hid-104-key-expansion` round. The goal is not to redesign the input architecture, but to allow more physical keys to be normalized into HID on both Windows and macOS without changing the current relay wire format, while keeping a clear legacy relay compatibility rule: relay keys when the mapping is stable, otherwise keep them explicitly local-only.

This round covers two expansion groups:

- Special control keys: `PrintScreen`, `ScrollLock`, `Pause`, `NumLock`, and the application/menu key
- JIS-specific keys: common Japanese keyboard-only keys, first added to HID and platform normalization in full, then evaluated individually for remote relay support based on mapping stability

The overall layering remains unchanged. HID is still the only shared keyboard representation inside `src/`, and `apps/nvda_remote/legacy_key_payload.py` remains the only boundary adapter allowed to handle `vk_code`, `scan_code`, and `extended`.

## Background

The previous round, documented in `docs/superpowers/specs/2026-06-12-hid-104-key-expansion-design_zh-TW.md`, expanded the HID-first model to full ANSI 104-key coverage plus the ISO extra key `NonUsBackslash`, and explicitly excluded the following keys from scope:

- JIS-specific keys
- `PrintScreen`
- `ScrollLock`
- `Pause`
- `NumLock`
- the application/menu key

The current codebase reflects the same boundary:

- `src/interop/key/hid.py` does not yet define these special keys or JIS keys
- the Windows and macOS HID mappings do not yet cover them
- `src/apps/nvda_remote/legacy_key_payload.py` does not yet handle relay-compatible conversions for them

As a result, this round is a follow-up to the existing HID expansion work, not an architecture reset.

## Goals

- Add special control keys and common JIS-specific keys to the shared HID constants.
- Complete native event -> HID normalization on both Windows and macOS for those keys.
- Support legacy relay payload conversion for special keys that have stable representations.
- Make JIS keys fully usable in local HID-first logic even when some of them cannot be relayed.
- Preserve the current control mode safety rule: unsupported relay keys must always be logged and locally suppressed, never passed through.

## Non-goals

- Do not change the existing NVDA Remote `type="key"` wire format.
- Do not add consumer/media keys or any keys outside HID `usage page` `0x07`.
- Do not spread relay compatibility logic into the Windows or macOS adapters.
- Do not invent approximate legacy mappings for special keys or JIS keys that cannot be defended technically.
- Do not guarantee end-to-end relay support for every JIS key.

## Scope

### In scope

#### Special control keys

The following keys are added to the shared HID model and should be prioritized for end-to-end relay support:

- `PrintScreen`
- `ScrollLock`
- `Pause`
- `NumLock`
- the application/menu key

#### JIS-specific keys

This round adds common JIS-only keys to HID and platform normalization in full. At minimum, this includes:

- `NonUsHash`
- `International1`
- `International3`
- `International4`
- `International5`

If the platform event model can reliably identify more Japanese-keyboard-specific usages, they may also be included, but this design does not require a broader region-keyboard research effort beyond the common JIS-only set.

### Keys that may remain local-only

The following kinds of keys may still remain local-only even after being added to HID, if the legacy payload cannot represent them reliably:

- some JIS-specific keys
- `Pause`, if its platform or legacy representation cannot be reconstructed in a stable way
- any key that would require guessed `scan_code` values, composite events, or ambiguous `extended` semantics

## Architecture

This round does not change the layering:

- `src/interop/key/*`: defines HID constants and the shared `KeyEvent`
- `src/adapters/windows/*`: normalizes Windows native events into HID
- `src/adapters/macos/*`: normalizes macOS native events into HID
- `src/application/*` and `src/apps/*`: consume HID only
- `src/apps/nvda_remote/legacy_key_payload.py`: converts HID into the legacy relay payload

The design principles remain:

- platform layers only perform native -> HID normalization
- core and app layers depend only on HID
- relay compatibility is handled at a single boundary

## Design decisions

### 1. Use HID-first + relay-best-effort

This round does not delay adding keys to HID just because relay compatibility may be limited. Every target key should first become part of the shared HID model and platform adapters. Relay support then follows a best-effort rule:

- keys that can be represented stably as `vk_code/scan_code/extended`: support relay
- keys that cannot be represented stably: remain explicitly local-only

This keeps the core model complete and prevents the old relay boundary from dictating the expressive limits of the input system.

### 2. Capturable does not automatically mean relay-capable

A key being capturable through the Windows hook or the macOS event tap is not enough to justify including it in the legacy relay adapter. The relay bar is higher:

- there must be a single defensible `vk_code`
- there must be a stable `scan_code`
- the `extended` meaning must be clear
- distinct HID usages must not be collapsed incorrectly into the same legacy key

If those conditions are not met, the key should stay local-only.

### 3. Bring JIS fully into HID first, then evaluate relay one key at a time

This round does not follow a strategy of trying only a small subset of JIS keys. Instead, it brings the common JIS-only keys fully into HID constants and platform mappings first. That allows:

- `key_echo`, local control logic, and future app logic to see those keys immediately
- a clean separation between "locally recognizable" and "relay-capable"
- avoiding a permanent state where JIS support is blocked behind endless pre-work research

The relay layer should review JIS keys individually rather than enabling them all at once.

### 4. Do not use approximate downgrade mappings

If a JIS key has no reliable legacy mapping, it should not be downgraded into a similar-looking ANSI key. If a special key has ambiguous `scan_code` or `extended` behavior, it should not be forced into an approximate legacy value.

Examples of explicitly disallowed behavior:

- mapping a JIS-specific key to an ordinary punctuation key
- mapping the application/menu key to another modifier or character key
- pretending an unstable multi-part Windows sequence is a single legacy payload

These would all break HID distinctions and make remote behavior unpredictable.

### 5. Unsupported relay keys keep the suppress + log rule

This round does not introduce a new forwarding state model. If `legacy_key_payload.py` rejects a HID key:

- `key_event_to_legacy_remote_payload()` should raise `ValueError`
- `NvdaRemoteInputForwardingUseCase` should log the failure clearly
- control mode should return `SUPPRESS`

This continues the safety logic established after the previous fix and prevents unsupported keys from affecting the local machine during remote control.

## Key-level strategy

### Keys prioritized for end-to-end relay

The following keys should be prioritized for HID coverage, platform mapping, and legacy relay mapping:

- `PrintScreen`
- `ScrollLock`
- `Pause`
- `NumLock`
- the application/menu key

If any one of them turns out not to have a stable relay representation, it may fall back to local-only, but that decision must be explicit in both tests and documentation rather than silently omitted.

### JIS key strategy

JIS keys are split into two capability levels:

- `HID-capable`: required. If Windows or macOS can recognize the key reliably, it must map to the appropriate usage.
- `Relay-capable`: optional, supported only when the legacy payload mapping is explicit and defensible.

So the definition of done for JIS in this round is not "all JIS keys relay end to end." It is:

- they are representable in shared HID
- they can be normalized at the platform layer
- their relay capability is decided explicitly key by key rather than left ambiguous

## File-level changes

### `src/interop/key/hid.py`

Add the following HID constant groups:

- special control keys: `PRINT_SCREEN`, `SCROLL_LOCK`, `PAUSE`, `NUM_LOCK`, `APPLICATION`
- JIS constants: `NON_US_HASH`, `INTERNATIONAL1`, `INTERNATIONAL3`, `INTERNATIONAL4`, `INTERNATIONAL5`

Keep them grouped within the same file without introducing a new abstraction layer.

### `src/adapters/windows/hid_map.py`

Add Windows `scanCode + extended` mappings, with `vkCode` used only where necessary, for the new HID usages.

Rules:

- still prefer `scanCode + extended`
- only consult `vkCode` when a special key needs disambiguation
- do not add fragile JIS mappings if they cannot be made stable

### `src/adapters/macos/hid_map.py`

Add macOS virtual key code mappings for the new HID usages.

Rules:

- prioritize JIS coverage because macOS usually exposes clearer key code distinctions for Japanese keyboard layouts
- add the other special keys only when the current event tap path can capture them reliably

### `src/apps/nvda_remote/legacy_key_payload.py`

Add defensible legacy mappings:

- for special control keys: add entries to `_USAGE_TO_LEGACY` when stable `vk_code/scan_code/extended` values exist
- for JIS keys: evaluate each key individually; supported ones are added, unsupported ones continue to raise `ValueError`

This module remains the only place that knows the details of the legacy payload.

### `src/apps/nvda_remote/use_cases/input_forwarding.py`

The behavior model does not change, but tests should expand to cover the new local-only keys:

- unsupported special keys: `SUPPRESS + log`
- unsupported JIS keys: `SUPPRESS + log`

## Data flow

### Local input

1. A platform adapter captures a native keyboard event.
2. The Windows/macOS mapping converts it into a HID `KeyEvent`.
3. `application` and `apps` consume only HID.
4. Even if a key cannot be relayed, local app logic can still recognize it.

### Remote forwarding

1. `nvda_remote` receives a HID `KeyEvent`.
2. If `legacy_key_payload.py` can convert it stably, it produces the existing `key` payload.
3. If it cannot convert the key stably, it raises `ValueError`.
4. The forwarding use case logs the failure and suppresses the key in control mode.

## Test strategy

### Unit tests: HID constants

Extend `tests/unit/test_hid_keys.py` with:

- usage-value tests for the special control keys
- usage-value tests for the JIS constants
- distinction tests against existing ANSI/ISO keys

### Unit tests: Windows adapter

Extend `tests/unit/test_windows_adapters.py` with:

- `PrintScreen`
- `ScrollLock`
- `Pause`
- `NumLock`
- the application/menu key
- every JIS key included in scope

The tests should validate the HID `KeyEvent` emitted from the hook callback directly, not just a helper function.

### Unit tests: macOS adapter

Extend `tests/unit/test_macos_adapters.py` with:

- special control keys that can be captured reliably through the event tap
- the JIS keys included in scope

If a key cannot be obtained reliably through the macOS path, the test should document that design limitation explicitly instead of silently omitting it.

### Unit tests: legacy relay adapter

Extend `tests/unit/test_nvda_remote_legacy_key_payload.py` with two categories:

- `relay-capable`: verify exact payload values
- `local-only`: verify that `ValueError` is raised

This test file should become the single source of truth for the relay capability of each newly added key.

### Unit tests: forwarding safety

Extend `tests/unit/test_nvda_remote_use_cases.py` with:

- unsupported special keys are suppressed in control mode
- unsupported JIS keys are suppressed in control mode
- log output contains enough identifying information for later debugging

## Risks

### 1. Special keys are not fully symmetrical across platforms

Keys like `Pause` and `PrintScreen` may not behave like ordinary single keys in every platform event model. Even if they can be captured locally, that does not guarantee that relay can reconstruct matching behavior reliably.

### 2. JIS and the legacy relay model have a fundamental semantic mismatch

Some JIS-only keys have clear HID usages, while the legacy relay path is still constrained by Windows-style `vk/scan/extended`. That means HID support and relay support will not fully overlap by default.

### 3. Incorrect downgrade mappings are more dangerous than explicit unsupported behavior

If approximate mappings are used just to increase apparent relay coverage, the remote side may receive the wrong key. That is harder to debug and more dangerous in control mode than keeping the key explicitly local-only.

## Conclusion

This round should treat special keys and JIS keys as the next controlled phase of the existing HID expansion work: first add them to HID and platform normalization, then apply a best-effort policy at the relay boundary, keeping keys explicitly local-only when they cannot be represented stably. That expands the real coverage of the shared keyboard input model without breaking the current architecture or safety model.
