# Legacy Payload Round-Trip on Main Design

## Goal

Keep the current `main`/`dev` payload policy explicit: HID-derived legacy
payloads are the default, while the opt-in Windows native compatibility mode
continues to use the captured Windows native tuple when available.

The previous feature branch's runtime safe set is not carried forward. Its
`KEYPAD_EQUALS` exception was based on an older mapping that used scan code
13; the current mapping uses scan code 89 and round-trips through the current
Windows HID map.

## Scope

- Do not add a runtime `ROUND_TRIP_SAFE_WINDOWS_HID_USAGES` policy set.
- Preserve `use_windows_native_key_payload` behavior in
  `legacy_payload_from_captured_event`.
- Add or strengthen regression coverage for every supported legacy HID
  mapping, including `KEYPAD_EQUALS`.
- Keep the existing `num_lock_on` behavior intact.

## Design

`legacy_payload_from_captured_event` remains a two-mode bridge:

1. Default mode converts the captured HID event through
   `key_event_to_legacy_remote_payload`, passing through the captured NumLock
   state.
2. Native compatibility mode returns `WindowsNativeKeyContext` values when a
   native context exists; otherwise it falls back to the HID conversion.

Round-trip tests will construct each supported HID event, convert it to a
legacy payload, feed that payload into `key_event_from_windows`, and assert
that the original HID usage is recovered. This verifies the mapping contract
without making the runtime bridge depend on a duplicated classification set.

## Validation

- Run the focused legacy payload and bridge tests.
- Run the full unit and integration test suite.

