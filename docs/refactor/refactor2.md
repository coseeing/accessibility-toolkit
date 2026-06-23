# Architecture refactor review v2

Context
-------
This review follows `docs/refactor/refactor1.md` and the output package
reorganization.

The codebase is now in a better state than the first review in several ways:
- `application.output` is now a real package instead of several output-related
  modules spread across `application/`.
- Speech backend selection is isolated under `application.output.speech`.
- Tone is represented as an output capability instead of being hidden in
  app-specific code.
- `apps/*/use_cases/` exists for parts of app logic, especially key echo and
  NVDA Remote control/input forwarding.
- Runtime field names are less redundant after moving output concepts under the
  output package.

The remaining issues are less about file placement and more about architectural
flow: runtime composition is still concentrated in app entrypoints, app services
still combine several responsibilities, and status/output/event flows are still
mostly ad hoc.

Primary architecture pressure points
------------------------------------

1. Runtime composition is duplicated across app entrypoints.

Files:
- `src/apps/nvda_remote/main.py`
- `src/apps/key_echo/main.py`
- `src/apps/access8graph/main.py`
- `src/bootstrap/platform.py`

Current state:
- Each app entrypoint assembles capture, hotkey capture, scheduler, speech,
  speaker, capabilities, app service, keyboard service, and UI app.
- `bootstrap/platform.py` contains platform detection, lazy imports, null
  fallbacks, clipboard factory, tone factory, and speech backend selection.
- The composition pattern is now more consistent, but still repeated.

Risk:
- A new app will copy a large portion of runtime wiring.
- Adding a new platform or backend still means editing central factory logic.
- App entrypoints remain hard to test without extensive monkeypatching.

Recommended direction:
- Introduce a shared runtime composition layer with app-specific hooks:
  - `bootstrap/providers.py` for platform capability providers
  - `bootstrap/output.py` for speech/tone capability assembly
  - `bootstrap/app_runtime.py` for common app runtime wiring
- Keep app `main.py` files focused on:
  - choosing app-specific service class
  - choosing default hotkey usage
  - creating the UI shell
  - starting the app loop

Migration order:
- Extract a `PlatformProvider` object from `bootstrap/platform.py`.
- Extract a shared `build_output_capabilities()` helper.
- Move common keyboard/hotkey/speech/speaker wiring out of each app `main.py`.
- Keep the existing factory functions as compatibility wrappers until tests are
  moved to the provider API.

2. App services are still facade/controller hybrids.

Files:
- `src/apps/nvda_remote/service.py`
- `src/apps/key_echo/service.py`
- `src/apps/access8graph/service.py`
- `src/apps/shared/speech_settings_controller.py`
- `src/apps/shared/mode_manager.py`

Current state:
- `NvdaRemoteAppService` owns connection/session behavior, mode switching,
  keyboard forwarding, clipboard push, speech settings, tone routing, status
  dispatch, input capture lifecycle, hotkey behavior, and transport message
  handling.
- `KeyEchoAppService` and `Access8GraphAppService` are smaller but still own
  both UI-facing controller methods and lower-level input/hotkey lifecycle.
- `ModeManager` is a useful shared abstraction, but app services still carry
  too much surrounding orchestration.

Risk:
- UI controllers depend on broad service objects instead of focused interfaces.
- Every new mode or app feature increases the surface area of one service class.
- Integration tests become the only practical way to verify behavior because
  individual responsibilities are not isolated enough.

Recommended direction:
- Treat app services as thin facades over focused use cases.
- Split NVDA Remote into at least these units:
  - `RemoteConnectionUseCase`
  - `RemoteControlUseCase`
  - `RemoteMessageHandlingUseCase`
  - `ClipboardSyncUseCase`
  - `RemoteStatusPresenter` or `StatusEventSink`
- Let UI-facing services delegate to these units instead of owning all logic.

Migration order:
- Start with `NvdaRemoteAppService`; it has the highest responsibility density.
- Extract transport/session connection logic first because it is separable from
  key forwarding.
- Extract status dispatch into typed events before splitting more UI-facing
  methods.
- Keep a small `NvdaRemoteAppService` facade until UI code has narrower
  dependencies.

3. Status and event flow should become typed.

Files:
- `src/apps/nvda_remote/service.py`
- `src/apps/access8graph/service.py`
- `src/apps/key_echo/service.py`
- `src/interop/protocol/routing/message_router.py`
- `src/interop/protocol/session/remote_session.py`
- `src/application/state.py`

Current state:
- App services publish status as dictionaries like
  `{"kind": "error", "message": ...}` and
  `{"kind": "speech_backend", "backend_id": ...}`.
- Remote session and router status also travels as loosely structured payloads.
- UI code implicitly depends on the shape of these dictionaries.

Risk:
- Event contracts are not discoverable from types.
- Renaming a status key or adding a new event shape can silently break UI.
- Shared application events and app-specific events are mixed together.

Recommended direction:
- Introduce typed event dataclasses.
- Separate shared runtime events from app-domain events.

Candidate shared events:
- `ErrorRaised`
- `InputCaptureChanged`
- `HotkeyCaptureChanged`
- `SpeechBackendChanged`
- `ClipboardAvailabilityChanged`

Candidate NVDA Remote events:
- `RemoteConnectionChanged`
- `RemoteControlChanged`
- `RemoteSessionJoined`
- `RemoteProtocolWarning`
- `RemoteTransportDisconnected`

Migration order:
- Add event dataclasses under `application/events.py` or
  `apps/shared/events.py`.
- Convert one app service to emit typed events internally while preserving the
  existing dict adapter at the UI boundary.
- Convert UI controllers to consume typed events directly.
- Remove the dict adapter after all app UIs are migrated.

4. Output is better organized, but still not a full multimodal architecture.

Files:
- `src/application/output/capabilities.py`
- `src/application/output/service.py`
- `src/application/output/scheduler.py`
- `src/application/output/manager.py`
- `src/application/output/speech/service.py`
- `src/adapters/outputs/interfaces.py`
- `src/apps/access8graph/output.py`

Current state:
- `Capabilities` exposes speech, tone, and braille slots.
- `QueuedService` coordinates speech queueing through a shared scheduler.
- Speech has backend management and settings; tone and braille are still simple
  optional adapter capabilities.
- `Manager` is still remote-message oriented: speech, cancel, pause, tone, and
  clipboard routing live together.

Risk:
- Tone, wave, and braille will become second-class if more behavior is added.
- Scheduling/interruption policy is speech-heavy.
- Apps that need coordinated output, such as speech plus tone or speech plus
  braille, will need custom orchestration.

Recommended direction:
- Evolve `Capabilities` into explicit output channels over time:
  - `SpeechChannel`
  - `ToneChannel`
  - `BrailleChannel`
  - `WaveChannel`
- Keep `Capabilities` as the app-facing bundle until channel behavior justifies
  a richer bus/router.
- Split `Manager` into a remote output handler if it remains tied to protocol
  messages.

Migration order:
- First define smaller protocols in `application.output`:
  - speech playback
  - speech settings
  - tone playback
  - braille display
- Move remote protocol output routing out of generic `Manager` naming.
- Add tone channel orchestration only when an app needs tone-specific queueing
  or cancellation policy.
- Defer a full `OutputBus` until at least two output channels need shared
  coordination.

5. Input architecture is partially reusable but not yet a shared command
pipeline.

Files:
- `src/application/input/`
- `src/application/keyboard.py`
- `src/apps/shared/mode_manager.py`
- `src/apps/key_echo/use_cases/echo_input.py`
- `src/apps/nvda_remote/use_cases/input_forwarding.py`
- `src/apps/access8graph/input.py`

Current state:
- Low-level capture is behind adapter protocols.
- `InputActivationUseCase` and `ModeManager` provide useful shared behavior.
- Apps still own key translation and command decisions in separate ways.

Risk:
- New apps will repeat keyboard pipeline logic.
- Hotkey enter/exit behavior can drift between apps.
- Accessibility graph navigation, key echo, and remote forwarding each encode
  command mapping differently.

Recommended direction:
- Build a shared input command pipeline:
  - captured event
  - normalized key event
  - app mode selection
  - command translation
  - app use-case execution
  - system pass-through decision
- Keep app-specific translators, but make their contract uniform.

Migration order:
- Introduce a shared `CommandTranslator` protocol.
- Adapt key echo and access8graph translators to that protocol first.
- Move system pass-through decisions into a single policy layer.
- Keep remote forwarding special-cased until typed remote key payloads are
  separated from local key events.

6. Repository hygiene should stop generated files from shaping architecture.

Files and directories:
- `src/**/*.pyc`
- `src/**/__pycache__/`
- generated install metadata such as `*.egg-info/`

Current state:
- The repo already removed tracked `egg-info` files.
- Local generated files still appear in the working tree and in broad file
  scans.

Risk:
- Generated files make architectural reviews noisier.
- Stale generated metadata can point at deleted modules and confuse future
  refactors.

Recommended direction:
- Keep generated Python caches, build outputs, and install metadata out of git.
- Add ignore rules for `*.egg-info/` if this has not already been done.
- Prefer source-level inventories from `git ls-files` when doing architecture
  reviews.

Target architecture
-------------------

Recommended long-term layering:

1. `interop/`
- Wire protocol messages, serialization, transport contracts, session mechanics.
- No wx, no platform imports, no app UI behavior.

2. `application/`
- Shared input, output, runtime events, scheduling, and capability contracts.
- No platform branches.
- No app-specific remote workflow.

3. `apps/shared/`
- Reusable app-facing controllers and mode orchestration.
- Shared presenters or typed event adapters for UI integration.

4. `apps/<app>/use_cases/`
- App-specific business behavior.
- Remote control, key echo, and graph navigation use cases live here.

5. `apps/<app>/service.py`
- Thin facade for UI and runtime wiring.
- Delegates to use cases and exposes a small screen-specific API.

6. `adapters/`
- Platform and driver implementations.
- Windows, macOS, future Linux, speech engines, tone/braille/wave drivers.

7. `bootstrap/`
- Provider selection, runtime composition, config paths, logging setup.
- This is the only place that should know how to assemble adapters into apps.

8. `ui/`
- wx views, frames, and UI controllers.
- Consumes app-facing interfaces and typed events.

Recommended roadmap
-------------------

Phase 1: Runtime provider extraction
- Extract platform provider objects from `bootstrap/platform.py`.
- Extract common app runtime wiring from app `main.py` files.
- Keep behavior unchanged and preserve existing tests.

Phase 2: Typed event migration
- Add event dataclasses for shared runtime events and app-domain events.
- Convert one app at a time to publish typed events internally.
- Keep a temporary adapter for existing UI dict payload expectations.

Phase 3: Split `NvdaRemoteAppService`
- Extract connection/session behavior.
- Extract remote message handling.
- Extract clipboard sync.
- Leave a thin UI-facing facade.

Phase 4: Output channel evolution
- Split output protocols by capability.
- Rename or narrow `Manager` if it remains protocol-message-specific.
- Add channel objects only where real coordination policy exists.

Phase 5: Shared input command pipeline
- Standardize command translator contracts.
- Move common pass-through and mode decision behavior into shared policies.
- Keep app-specific command mapping isolated.

Phase 6: UI dependency narrowing
- Make each frame depend on a small controller protocol.
- Avoid passing full app services into UI classes when only a subset is needed.
- Replace broad monkeypatch-heavy tests with controller-level tests where
  possible.

Recommended next milestone
--------------------------

If only one long-term refactor should start next, start with runtime provider
extraction.

Reason:
- It reduces duplication across all app entrypoints.
- It creates a natural place for platform and output provider registration.
- It makes later app-service splitting easier because app services will receive
  cleaner dependencies.
- It is less behaviorally risky than splitting `NvdaRemoteAppService` first.

The second milestone should be typed events. Without typed event contracts,
service splitting will keep moving loosely structured dictionaries around and
will not significantly improve the UI/application boundary.
