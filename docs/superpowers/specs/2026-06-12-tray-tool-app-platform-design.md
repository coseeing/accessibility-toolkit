# Tray Tool App Platform Design

## Purpose

Build a reusable app platform for `nvda_remote`, `key_echo`, and future utility apps so that new apps can share:

- a resident system-status-icon startup model
- a shared icon menu
- main-panel and speech-settings-panel lifecycle handling
- an input switching model for multiple active/inactive modes
- speech settings control logic

The goal of this phase is not to apply more design patterns or make the current architecture fully generic. The goal is to shape the app shell and mode behavior that are already repeating into a reusable foundation driven by the next-stage requirements, reducing the cost of adding a third or fourth utility app.

## Background

The project already has some reusable building blocks:

- protocol boundaries such as `Transport`, `SpeechOutput`, and `InputCapture`
- `InputActivationUseCase` for active/inactive capture switching
- `ActiveKeyEventPolicy` for active-state key routing
- a facade-plus-use-case composition style in `KeyEchoAppFacade` and `NvdaRemoteAppFacade`

But there are also clear structural problems:

- app facades currently own lifecycle, input orchestration, status dispatch, and speech-settings proxy behavior at the same time
- the shared app-shell behavior between `key_echo` and `nvda_remote` has not been extracted yet
- speech settings use cases are nearly duplicated across the two apps
- the UI still revolves around directly opening windows instead of a resident system-status-icon model
- there is no explicit mode model for future apps that need multiple active/inactive features in the same app

## Next-Phase Requirements Summary

Future utility apps need to support the following shared behavior:

1. Enter full keyboard-capture mode using a hotkey, and leave it from the active state using the same or a different hotkey.
2. Allow multiple such features inside a single app, where each feature has its own enter/exit hotkeys and active keyboard behavior.
3. Stay resident behind a system status icon; on Windows this is a tray icon, and on macOS this is a menu bar status item. Users open the main panel, speech settings, or exit the program from the icon menu.
4. Closing the main panel should only hide the window, not exit the program. Full exit must go through the icon menu’s `Exit` action.
5. Speech settings should be a shared standalone panel opened from the icon menu.

These requirements are informed in part by NVDA’s current `wx.App + hidden MainFrame + TaskBarIcon` model.

## Design Patterns vs SOLID Review

### What is already working

- `Protocol` is used as the app’s port boundary, which supports dependency inversion.
- The app layer uses facades to coordinate use cases instead of letting the UI talk directly to transports or adapters.
- `SpeechBackendManager` already acts as a strategy selector with a real variation point behind it.

### What is actually wrong right now

- `NvdaRemoteAppFacade` and `KeyEchoAppFacade` are both starting to take on too many responsibilities, which puts visible pressure on `SRP`.
- The two apps share lifecycle, speech settings, status listener, and capture-bind structure, but that structure has not become a stable shared layer.
- `RuntimeState` and the remote/session flow in `nvda_remote` are not suitable as the common state core for all future utility apps.

### Directions this phase should avoid

- do not introduce a large event bus or mediator first
- do not build a large `BaseAppFacade` inheritance hierarchy first
- do not genericize remote session/protocol logic across all utility apps first

The reason is simple: these moves make the architecture look more pattern-heavy, but they do not directly serve the current expansion requirements. They would be overlay design.

## Design Goals

1. Make it unnecessary to rebuild a status-icon shell, panel handling, speech settings, and input activation skeleton for each new utility app.
2. Allow a single app to register multiple modes, where each mode brings its own enter/exit hotkeys and active keyboard behavior.
3. Draw a clear boundary between shared shell behavior and app-specific business behavior.
4. Preserve the remote/session special cases in `nvda_remote` without forcing every utility app to depend on that model.
5. Let `key_echo` and future small utility apps benefit from the platform first, then gradually connect `nvda_remote` to the reusable parts.

## Non-Goals

- redesigning the full protocol, relay, or session architecture
- dynamic plugin or app loading
- editable hotkey configuration UI
- rewriting all app state flow into typed events
- merging all apps into a single mega-app

## Recommended Approach

Adopt a **Tray Tool App Platform**.

The central idea is to split the repeated structure into four stable boundaries:

1. `TrayAppShell`
2. `ModeManager`
3. `PanelController`
4. `SpeechSettingsController`

Each app keeps its own business use cases and only registers:

- app metadata
- the main panel
- the list of modes
- extra menu items, if needed

## Architecture Overview

```text
wx.App
  -> TrayAppShell
       -> TaskBarIcon / status item menu
       -> PanelController
       -> SpeechSettingsController
       -> ModeManager
            -> ActivationMode A
            -> ActivationMode B
            -> ActivationMode C
       -> App-specific facade / use cases
```

The platform layer is responsible for how a resident utility app runs.

The app layer is responsible for what the app’s modes actually do.

## Core Components

### TrayAppShell

Responsibilities:

- start `wx.App`
- create a cross-platform `TaskBarIcon`
- manage the shared icon menu
- manage app shutdown flow
- coordinate panel show/hide behavior with `PanelController`
- coordinate startup mode binding with `ModeManager`

Fixed shared icon menu:

- Main Panel
- Speech Settings
- Exit

Non-responsibilities:

- app-specific business logic
- remote protocol/session
- active-mode internal key-handling rules

### PanelController

Responsibilities:

- create and register the main panel and speech settings panel
- handle show / hide / focus / restore consistently
- intercept window-close events and convert them into hide behavior
- provide a single icon-menu entry point for opening panels

Design requirements:

- closing the main panel should only call `Hide()`, not exit the app
- closing the speech settings panel should also only hide it
- real app shutdown is handled centrally by `TrayAppShell`

### SpeechSettingsController

Responsibilities:

- wrap `SpeechOutputService` backend/voice/rate/pitch/volume operations
- expose the query and update API needed by the speech settings panel
- optionally support a backend-changed callback

This component replaces the duplicated logic currently found in:

- `src/apps/nvda_remote/use_cases/speech_settings.py`
- `src/apps/key_echo/use_cases/speech_settings.py`

### ActivationMode

`ActivationMode` represents one activatable feature inside an app.

Each mode should define at least:

- `mode_id`
- `enter_hotkey`
- `exit_hotkey`
- `can_enter() -> bool`
- `enter() -> bool`
- `exit() -> bool`
- `handle_key_event(event) -> KeyEventDecision`

Notes:

- `enter_hotkey` is used from `HotkeyCapture` while the app is idle
- `exit_hotkey` is used from `InputCapture` while the app is active
- `handle_key_event` defines the remaining key behavior while active

### ModeManager

Responsibilities:

- register multiple `ActivationMode` objects
- listen for mode activation hotkeys while idle
- guarantee that only one mode is active at a time
- switch between `HotkeyCapture` and `InputCapture`
- route keyboard events to the current active mode
- publish mode status for UI or icon-menu display

`ModeManager` should not know:

- that remote session logic exists
- the concrete business rules of speech echo
- how each app’s panels are laid out

### Cross-Platform Icon Behavior

`TaskBarIcon` in this design should be treated as a cross-platform system-status-icon abstraction:

- Windows: notification area / tray icon
- macOS: menu bar status item

Implementation requirements:

- do not hard-code the interaction model as a Windows right-click tray pattern
- prefer `wx.adv.TaskBarIcon.CreatePopupMenu()` or `GetPopupMenu()` as the menu-display model
- do not assume every platform fully supports the same mouse events or `PopupMenu()` behavior

This avoids leaking Cocoa-specific event differences into the platform design.

### ModeActivationCoordinator

This layer can evolve from the current `InputActivationUseCase`.

Responsibilities:

- switch active/inactive capture ownership
- keep `HotkeyCapture` and `InputCapture` mutually exclusive
- recover when transitions fail

Difference from the current model:

- today it only expresses whether the app is active
- next phase it needs to express which mode is active

### ActiveKeyEventPolicy

The current `ActiveKeyEventPolicy` concept can stay, but it should stop being implicitly tied to a single app.

Suggested evolution:

- the exit key comes from the current active mode
- non-exit keys are handled through the active mode’s `handle_key_event()`
- the policy owns routing, not business rules

## App Boundaries

### What belongs in the platform layer

- system status icon and shared icon menu
- main panel and speech settings panel show/hide lifecycle
- speech settings controller
- active/inactive capture switching
- mode registry and mode routing
- shared status notifier

### What should remain app-specific

- `nvda_remote`’s `RemoteSession`
- `nvda_remote`’s `MessageRouter`
- remote key forwarding and clipboard rules
- `key_echo`’s speech-echo content rules
- each app’s main-panel content and app-specific actions

## File and Module Recommendations

Recommended shared app-platform area:

```text
src/apps/shared/
  tool_app_shell.py
  panel_controller.py
  speech_settings_controller.py
  mode_manager.py
  mode_types.py
  tray_icon.py
```

Suggested responsibilities:

- `tool_app_shell.py`
  - app startup, shutdown, menu wiring
- `panel_controller.py`
  - main-panel and speech-settings-panel show/hide management
- `speech_settings_controller.py`
  - shared speech settings query and update logic
- `mode_manager.py`
  - mode registration, hotkey activation, active-key routing
- `mode_types.py`
  - `ActivationMode` protocol or dataclass
- `tray_icon.py`
  - cross-platform wx `TaskBarIcon` wrapper

## Relationship to Existing Files

### Existing files to converge first

- `src/apps/nvda_remote/use_cases/speech_settings.py`
- `src/apps/key_echo/use_cases/speech_settings.py`
- `src/application/input/activation.py`
- `src/application/input/active_key_policy.py`
- `src/ui/nvda_remote/app.py`
- `src/ui/echo/app.py`

### Existing files that should not be pulled into the shared platform first

- `src/apps/nvda_remote/facade.py`
- `src/interop/protocol/session/remote_session.py`
- `src/interop/protocol/routing/message_router.py`
- `src/application/state.py`

Why:

- `nvda_remote` has strong remote-specific behavior and should only adopt the shared shell/mode/lifecycle pieces, without polluting the platform layer with remote special cases.
- `RuntimeState` is currently remote-centric and is not a good common state root for the utility-app platform.

## How Existing Apps Should Land on the Platform

### key_echo

`key_echo` should be the first app to fully adopt the platform.

Its first phase can start with a single mode:

- `echo_keys_mode`
  - enter hotkey: `Enter`
  - exit hotkey: `Escape`
  - active behavior: speak the pressed key

Later additions such as:

- `echo_shortcuts_mode`
- `speak_selection_mode`
- `announce_key_category_mode`

should only require adding modes, not rebuilding the shell.

### nvda_remote

`nvda_remote` should adopt the platform in two stages:

1. first connect to the icon shell, panel controller, and speech settings controller
2. then connect control-mode capture lifecycle to `ModeManager`

Its mode set can initially stay as a single mode:

- `remote_control_mode`
  - enter hotkey: `F11`
  - exit hotkey: `F11`
  - active behavior: remote key forwarding

But the following should remain app-specific:

- `RemoteSession`
- `MessageRouter`
- connection status handling
- clipboard push/set rules

## Refactor Sequence

### Phase 1

Extract `SpeechSettingsController`, merge the duplicated speech settings use cases, and connect both `key_echo` and `nvda_remote` to it.

Purpose:

- low risk
- high payoff
- establishes the first stable shared platform capability
- validates the shared layer with both apps from the first step

### Phase 2

Introduce `PanelController`, make both the main panel and speech settings panel hide-on-close, and apply it to both `key_echo` and `nvda_remote`.

This phase can fix window lifecycle first without yet introducing the system status icon.

### Phase 3

Introduce `TrayAppShell` and the shared icon menu, and make both `key_echo` and `nvda_remote` support the basic resident-status-icon flow: stay resident, open the main panel, open speech settings, and exit through the menu.

After this, app startup should behave like this:

- the app starts and stays resident behind the system status icon
- the main panel opens from the icon menu
- speech settings opens from the icon menu
- full exit happens only through the icon menu’s `Exit`

### Phase 4

Introduce `ModeManager`, and let `key_echo` adopt it first with a single mode to validate the contract.

This phase uses `key_echo` first not because it is the only target, but because it is the lower-risk app for validating:

- whether the `ActivationMode` interface is stable
- whether the enter/exit hotkey contract is sufficient
- whether active keyboard routing is clear
- whether the boundary between modes and the panel/icon shell stays clean

### Phase 5

Connect `nvda_remote` to the shared active/inactive lifecycle in `ModeManager` while preserving remote-specific orchestration.

This phase should only adopt the following shared capabilities:

- mode enter/exit lifecycle
- active/inactive capture switching
- active key routing contract

This phase should still keep these app-specific concerns in place:

- `RemoteSession`
- `MessageRouter`
- connection status handling
- clipboard push/set rules

This validates whether the platform also works for the more complex app without pushing remote-specific behavior into the platform core too early.

### Phase 6

Validate the platform against a third new utility app.

Success criteria:

- a new app does not need to rebuild the status-icon shell
- a new app does not need to rebuild the speech settings panel
- a new app does not need to rebuild active/inactive capture switching
- a new app only needs to register modes, a main panel, and a small amount of app-specific use-case logic

## Validation Strategy

This design uses a **two-app, staged validation** approach.

Why:

- if only `key_echo` adopts the platform, the platform may collapse into an abstraction that only serves simple apps
- if both `key_echo` and `nvda_remote` fully adopt `ModeManager` at the same time, the risk and debugging cost become too high

So validation happens in two layers:

1. both `key_echo` and `nvda_remote` validate the shared shell/panel/speech-settings layer first
2. `ModeManager` is validated first by `key_echo`, then by `nvda_remote` as the more complex remote app

This sequence balances:

- whether the platform is truly general
- whether problems are easy to localize
- whether `nvda_remote` special cases contaminate the platform core

## Risks and Tradeoffs

### Risk 1: extracting too early into inheritance

If a `BaseAppFacade` is introduced too early, it may reduce duplication in the short term, but it is likely to be polluted by hooks and conditionals once `nvda_remote` special cases accumulate.

Tradeoff:

- this design prefers composition over inheritance

### Risk 2: pulling remote-specific state into the platform

If the platform starts sharing `RuntimeState` or `RemoteSession` concepts, future utility apps will be tied to remote concepts they do not need.

Tradeoff:

- the platform only handles shell and mode lifecycle
- remote-specific state and flow remain inside `nvda_remote`

### Risk 3: over-generic hotkey modeling

If this phase tries to support arbitrary commands, editable mappings, and persistent configuration from the start, the scope will expand significantly.

Tradeoff:

- this phase only handles mode enter/exit hotkeys and active keyboard behavior

## Testing Strategy

### Unit tests

Add or adjust test coverage for:

- `SpeechSettingsController` backend/voice/rate/pitch/volume behavior
- `ModeManager` mode registration, single-active-mode guarantees, and transition-failure recovery
- `PanelController` close-to-hide behavior
- `TrayAppShell` menu action wiring

### Integration tests

Preserve and expand:

- `key_echo` active-entry, active-exit, and key-handling flow
- `nvda_remote` control-mode transitions and capture lifecycle

### Behavior validation

At minimum, verify these cases:

1. app startup does not automatically open the main panel and only leaves the app resident behind the system status icon
2. choosing `Main Panel` from the icon menu shows the window
3. closing the main panel only hides it and does not exit the app
4. choosing `Speech Settings` from the icon menu shows the shared panel
5. choosing `Exit` from the icon menu is the only full shutdown path
6. multiple modes in the same app cannot be active at the same time
7. an active mode’s exit hotkey restores idle capture correctly

## Implementation Summary

The most important thing in this phase is not adding more patterns. It is stabilizing these four boundaries:

1. app shell boundary
2. mode boundary
3. shared panel boundary
4. remote-specific boundary

If these boundaries are stable, adding future utility apps becomes materially cheaper. If not, then event buses, base facades, and giant generic state machines will only produce a more abstract architecture, not a better one.
