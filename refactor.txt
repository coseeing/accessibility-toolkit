SOLID review for src/
=====================

Goal context
------------
Long-term goal: build a reusable input/output foundation for upper-layer applications, especially:
- input: keyboard hook and future input devices or hotkeys
- output: speech, tones, wave/sound effects, braille
- app layer: thin use-case orchestration on top of shared capabilities

High-priority findings
----------------------

1. Composition roots currently contain platform selection, lazy imports, logging setup, config path policy, backend wiring, and app object construction.
Files:
- src/apps/nvda_remote/main.py
- src/apps/key_echo/main.py

Impact:
- Violates SRP. These modules are doing bootstrap, platform detection, infrastructure wiring, and runtime policy.
- Violates OCP. Adding a new platform or output backend requires editing these entry modules directly.
- Makes future reuse hard. A third app would duplicate more of this wiring.

Recommendation:
- Extract a shared runtime builder layer, for example:
  - src/bootstrap/platform.py
  - src/bootstrap/output_registry.py
  - src/bootstrap/runtime_factory.py
- Keep app main modules as thin entrypoints:
  - configure process
  - ask runtime factory for AppRuntime
  - start UI/app loop

2. App services mix use-case orchestration with device lifecycle control and transport event handling.
Files:
- src/apps/nvda_remote/service.py
- src/apps/key_echo/service.py

Impact:
- Violates SRP. NvdaRemoteAppService handles connection flow, control mode state, keyboard forwarding, hotkey toggling, message routing, clipboard, speech backend UI concerns, and error/status dispatch.
- Violates ISP. The UI effectively depends on a large ad hoc controller surface instead of focused interfaces.
- Future apps will either copy this pattern or inherit too much behavior.

Recommendation:
- Split app services into narrower use cases:
  - ConnectionController / RemoteSessionController
  - ControlModeController
  - InputForwardingUseCase
  - SpeechSettingsUseCase
  - ClipboardSyncUseCase
- UI should depend on a presenter or controller interface tailored to that screen, not the full service object.

3. Output abstraction is speech-centric and not yet a true multimodal output architecture.
Files:
- src/application/output_service.py
- src/application/output_capabilities.py
- src/application/services.py
- src/adapters/outputs/interfaces.py

Impact:
- The shared output layer is effectively "speech backend management with some optional tone/braille fields".
- Tone, wave, and braille have protocols, but there is no equivalent application service model for them.
- This will not scale cleanly when upper-layer apps need coordinated output policies such as:
  - speak + tone together
  - interrupt speech but not sound effect
  - queue tones independently from speech
  - route output by capability availability

Recommendation:
- Introduce a capability-oriented output facade, for example:
  - OutputBus or OutputRouter
  - SpeechChannel
  - ToneChannel
  - WaveChannel
  - BrailleChannel
- Define separate service protocols per capability instead of one speech-heavy interface.
- Move scheduling policy to per-channel or coordinated output orchestration rather than burying it inside speech implementations only.

4. Protocol and app event flow is dictionary-based and weakly typed.
Files:
- src/apps/nvda_remote/service.py
- src/interop/protocol/routing/message_router.py
- src/interop/protocol/session/remote_session.py
- src/application/state.py

Impact:
- Violates ISP and DIP in practice because many layers communicate through loosely structured dict payloads and stringly typed states.
- Harder to evolve safely when more event types, device events, or output events are introduced.
- Increases coupling between UI expectations and internal status payload shapes.

Recommendation:
- Replace status dicts with typed domain events, but keep remote-specific events out of the shared foundation:
  - shared capability/runtime events:
    - InputCaptureStarted
    - InputCaptureStopped
    - ErrorRaised
    - SpeechBackendChanged
    - ClipboardAvailabilityChanged
  - remote domain events:
    - RemoteConnectionStateChanged
    - RemoteControlStateChanged
    - RemoteSessionJoined
    - RemoteVersionMismatch
- Replace RuntimeState string unions with stricter state models and transitions.
- MessageRouter and RemoteSession should emit typed events, not generic dict payloads.

SOLID by principle
------------------

S: Single Responsibility Principle
- Good:
  - src/interop/protocol/serializer.py is focused.
  - src/interop/key/key_event.py is focused.
- Needs work:
  - src/apps/nvda_remote/main.py has too many reasons to change.
  - src/apps/nvda_remote/service.py has too many reasons to change.
  - src/application/output_service.py mixes speech control proxying with scheduler shutdown lifecycle.

Refactor target:
- one module for process/bootstrap
- one module for platform adapter resolution
- one module per use case
- one module per output capability orchestration concern

O: Open/Closed Principle
- Current platform/backend selection is mostly if/else on sys.platform plus hidden import wiring.
- Adding Linux, another speech backend, or another input source will require editing central files.

Refactor target:
- register adapters/backends through factories:
  - InputCaptureFactory
  - HotkeyCaptureFactory
  - ClipboardFactory
  - SpeechBackendRegistry
  - OutputCapabilityRegistry
- app code asks for capabilities by interface, not by platform branch

L: Liskov Substitution Principle
- Current protocols are mostly small and reasonable for substitution.
- Risk area: speech implementations implicitly carry different behavioral guarantees:
  - pyttsx3 uses OutputScheduler heavily
  - NVDA controller has different pause/voice semantics
  - NullSpeechOutput is incomplete relative to the full protocol shape expected elsewhere

Refactor target:
- define explicit capability contracts and optional features:
  - SupportsVoices
  - SupportsPause
  - SupportsProsody
- do not force every speech adapter to fake unsupported features under one fat protocol

I: Interface Segregation Principle
- Biggest issue in current design.
- SpeechOutput and SpeechOutputService are broad UI-oriented interfaces.
- App services expose large controller-like surfaces that every screen consumes wholesale.

Refactor target:
- split interfaces by use case:
  - SpeechPlayback
  - SpeechVoiceConfiguration
  - SpeechProsodyConfiguration
  - ClipboardRead
  - ClipboardWrite
  - InputCaptureControl
  - HotkeyCaptureControl
- let each UI screen depend only on the subset it needs

D: Dependency Inversion Principle
- There is some good protocol usage already:
  - Transport
  - InputCapture
  - HotkeyCapture
  - ClipboardService
- But composition roots and services still know too much concrete platform detail.
- importlib-based lazy loading hides dependency problems rather than modeling them.

Refactor target:
- move platform discovery behind provider objects:
  - PlatformInputProvider
  - PlatformOutputProvider
  - PlatformPermissionProvider
- high-level app services depend on these abstractions, not on runtime import logic

Architecture recommendation
---------------------------

Recommended target layering:

1. interop/
- protocol framing, wire models, serializers, transport contracts

2. domain/
- key events, speech/tone/wave/braille commands
- shared capability/runtime events
- remote domain state models and events when remote features are involved

3. application/
- use cases only
- no platform branches
- no importlib lazy loading
- no wx types

4. infrastructure/
- windows/, macos/, future linux/
- input hooks, clipboard, speech drivers, tone/wave/braille drivers
- provider/factory implementations

5. bootstrap/
- runtime composition
- configuration loading
- logging setup
- platform/provider registration

6. ui/
- wx views and presenters/controllers
- depends on application interfaces only

Concrete refactor steps
-----------------------

Phase 1: stabilize boundaries
- Extract typed status/event classes from dict payload usage, but split shared capability events from remote-specific events.
- Move logging/config path logic out of app main modules into bootstrap helpers.
- Extract platform adapter resolution from app main modules into providers/factories.

Phase 2: split oversized services
- Break NvdaRemoteAppService into focused use-case classes.
- Keep a thin facade only if UI convenience is needed.
- Remove direct transport/input/hotkey lifecycle juggling from one class.

Phase 3: redesign output architecture
- Introduce first-class output channels for speech, tone, wave, braille.
- Replace OutputCapabilities dataclass with an output service registry or output bus.
- Give each capability its own contract and scheduling/interruption policy.

Phase 4: unify input architecture
- Define a shared input event pipeline:
  - raw capture
  - normalized input event
  - command mapping / hotkey policy
  - app use-case handling
- This prevents app services from owning low-level key semantics directly.

Phase 5: app-facing SDK surface
- Expose reusable application interfaces so future apps can be built without knowing platform details:
  - InputService
  - OutputServiceRegistry
  - ConnectionUseCases if remote features are needed
  - Event subscription API

Suggested file-level changes
----------------------------

- src/apps/nvda_remote/main.py
  Split into bootstrap/process entrypoint and nvda_remote runtime assembly.

- src/apps/key_echo/main.py
  Reuse the same bootstrap/runtime assembly pattern instead of maintaining another custom composition root.

- src/apps/nvda_remote/service.py
  Extract connection, control, clipboard, speech-settings, and hotkey-toggle responsibilities.

- src/apps/key_echo/service.py
  Convert into a thin use-case facade over reusable input and speech application services.

- src/application/output_service.py
  Stop modeling all output concerns as a speech service plus scheduler shutdown wrapper.

- src/application/services.py
  Either narrow OutputManager to a specific remote-output use case or move clipboard/speech handling into dedicated use cases.

- src/adapters/outputs/interfaces.py
  Split broad speech contract into smaller optional capability contracts.

- src/application/state.py
  Replace permissive string unions with stronger typed state transitions or state objects.

Residual risks if not refactored
--------------------------------
- Every new app entrypoint will duplicate composition and platform logic.
- Tone/wave/braille support will remain second-class and awkward to orchestrate.
- UI and application logic will keep coupling through ad hoc controller methods and dict events.
- Platform expansion will increase conditional complexity instead of adding pluggable providers.

Recommended first milestone
---------------------------
If only one refactor is funded first, do this:

Extract a shared bootstrap/provider layer and split NvdaRemoteAppService.

That gives the highest leverage because it improves SRP, OCP, ISP, and DIP at once, and it creates the seam needed for the later multimodal input/output architecture.
