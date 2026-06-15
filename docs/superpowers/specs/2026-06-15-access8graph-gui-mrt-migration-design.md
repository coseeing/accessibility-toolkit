# Access8Graph GUI MRT Migration Design

## 1. Context

Access8Graph is an NVDA add-on for navigating accessible structure diagrams, especially MRT-style route graphs authored as yEd GraphML. Its current implementation depends on NVDA runtime APIs for keyboard hooks, focus objects, speech, tones, and review text. The parser, MRT model, and navigator are comparatively independent and can be reused outside NVDA with limited adaptation.

This project already provides the shared architecture needed for that migration:

- Keyboard input capture through `KeyboardInputService`, `InputCapture`, and `HotkeyCapture`.
- App-level key handling through `AppKeyEventResult` and `KeyboardPipelineResult`.
- Speech output through `OutputCapabilities.speech`.
- A tray-based wxPython tool shell used by `key_echo`, including main panel, speech settings, and exit actions.

The first migration step is a GUI MVP that mirrors `key_echo`: a main panel chooses a `.graphml` file and starts or stops graph navigation. Speech settings and tray behavior stay shared.

## 2. Goals

- Add a new `apps.access8graph` application and `ui.access8graph` GUI.
- Reuse the existing `ToolAppShell`, tray icon, and `SpeechSettingsFrame`.
- Support choosing only `.graphml` files from the main panel.
- Start MRT graph navigation from the selected file using this repository's keyboard capture and speech output.
- Preserve the existing Access8Graph MRT flow behavior for mode selection, station/line lists, direction exploration, linear exploration, route planning, transfer menus, and help menus.
- Keep the migrated GraphML parser, MRT model, and navigator testable without NVDA imports.

## 3. Non-goals

- Do not migrate `directedGraphView.py` or the older generic directed graph prototype.
- Do not implement Windows Explorer selected-file integration or the original `NVDA+alt+g` add-on entry point.
- Do not implement NVDA review text or NVDA focus-object behavior in the first stage.
- Do not add GraphML authoring validation or schema enforcement.
- Do not redesign Access8Graph's MRT interaction model.

## 4. User Experience

The Access8Graph app starts as a tray tool, matching `key_echo`.

Tray menu:

- `Main`: opens the Access8Graph main frame.
- `Speech Settings`: opens the shared speech settings frame.
- `Exit`: shuts down input capture, speech output, and the wx app.

Main frame:

- `Choose GraphML...`: opens a file picker filtered to `.graphml`.
- Status text:
  - `No file selected` before file selection.
  - The selected file name after choosing a file.
  - `Navigation running` after navigation starts.
  - A concise error message if loading or starting fails.
- `Start Navigation` / `Stop Navigation`:
  - Disabled until a `.graphml` file is selected.
  - Starts navigation for the selected graph.
  - Changes to `Stop Navigation` while keyboard capture is active.

When navigation starts, the app speaks the MRT mode menu. Users then operate the graph using the existing MRT flow keys, including arrows, Enter, `q`, `h`, `m`, `v`, `d`, `u`, `p`, `s`, `l`, and `e`. Escape exits navigation and returns the app to idle state.

## 5. Architecture

### Modules

`apps.access8graph.main`

- Builds runtime dependencies the same way `apps.key_echo.main` does.
- Creates input capture, hotkey capture, speech scheduler, speech service, output service, app service, and wx app.
- Uses shared speech backend defaults.

`apps.access8graph.service`

- Owns selected file path and navigation running state.
- Exposes UI-facing methods:
  - `choose_graphml(path: str)`.
  - `start_navigation()`.
  - `stop_navigation()`.
  - `is_navigation_running()`.
  - speech settings proxy methods matching `key_echo`.
- Implements `handle_key_event(CapturedKeyEvent) -> KeyboardPipelineResult`.
- Activates keyboard capture while navigation is running and restores idle state on stop.

`apps.access8graph.graphml`

- Contains migrated Access8Graph GraphML parser, MRT model, and MRT navigators.
- Must not import NVDA modules.
- Keeps behavior close to the source Access8Graph files to reduce migration risk.

`apps.access8graph.flow`

- Contains the migrated MRT flow and state machine from `mrtView.py`.
- Keeps `State`, `ListState`, `HelpState`, `ListView`, and `RunView`.
- Replaces NVDA `Window`, `speech`, `tones`, `textInfos`, focus, and logging dependencies with explicit adapters.

`apps.access8graph.input`

- Converts this repository's `KeyEvent` values into MRT flow command keys.
- Tracks only key-down events for commands, matching Access8Graph's original behavior.
- Ignores key-up events except for pipeline suppression while active.

`ui.access8graph.app`

- Mirrors `ui.echo.app`.
- Creates `ToolAppShell` with `Access8GraphMainFrame` and shared `SpeechSettingsFrame`.

`ui.access8graph.main_frame`

- Provides the file picker, status text, and start/stop button.
- Updates UI from controller status notifications.

### Data Flow

1. User opens the main frame from the tray.
2. User clicks `Choose GraphML...` and selects a `.graphml` file.
3. UI calls `controller.choose_graphml(path)`.
4. User clicks `Start Navigation`.
5. Controller loads:
   - `Graph(path=path)`.
   - `MrtModel(Graph)`.
   - `MrtDirectionNavigator(MrtModel)`.
   - `MrtUndirectionNavigator(MrtModel)`.
   - `MrtFlow({"direction": ..., "undirection": ...}, output=...)`.
6. Controller enters active keyboard capture through the existing activation pattern.
7. Captured key events are translated to flow commands.
8. `MrtFlow.enter(command)` updates state and emits speech or failure beep.
9. Escape or the Stop button exits navigation and restores idle state.

## 6. Flow Adaptation

The original Access8Graph `MrtFlow` does three NVDA-specific jobs:

- Focus lifecycle through `Window`, `event_gainFocus`, and `event_loseFocus`.
- Speech and tones through NVDA `speech` and `tones`.
- Review text through `GraphViewTextInfo`.

The migration keeps the flow's state machine but removes these responsibilities.

New flow responsibilities:

- Hold navigators and state objects.
- Accept a command dict with `key`, `repeat`, and `pressing`.
- Normalize command keys in the same way as the original flow:
  - Remove `kb:` prefix if present.
  - Map arrow keys to `up`, `down`, `left`, `right`.
  - Treat Enter as `onok()`.
- Emit output through injected callbacks:
  - `cancel_speech()`.
  - `speak(items: tuple[str, ...])`.
  - `beep_failure()`.
- Return whether the command was handled.

Review text is not part of the first-stage runtime. If later needed, the current `state.view.label` can be exposed as a plain property for a future review-text adapter.

## 7. Input Mapping

`Access8GraphKeyTranslator` maps HID keyboard events to command names.

Supported first-stage mappings:

- `HID.UP` -> `up`.
- `HID.DOWN` -> `down`.
- `HID.LEFT` -> `left`.
- `HID.RIGHT` -> `right`.
- `HID.ENTER` and `HID.KEYPAD_ENTER` -> `enter`.
- `HID.ESCAPE` -> `escape`.
- Letter keys used by the MRT flow:
  - `D` -> `d`.
  - `U` -> `u`.
  - `P` -> `p`.
  - `Q` -> `q`.
  - `H` -> `h`.
  - `M` -> `m`.
  - `V` -> `v`.
  - `S` -> `s`.
  - `L` -> `l`.
  - `E` -> `e`.
- `HID.HOME` -> `home`.
- `HID.END` -> `end`.

The translator returns no command for unsupported keys. While navigation is active, unsupported keys are still treated as handled and suppressed, because the original Access8Graph hook swallowed most keys inside its interaction window.

Escape is handled by the service before dispatching to flow. It stops navigation and returns `HANDLED_STOP`.

## 8. Output Behavior

`Access8GraphFlowOutput` adapts flow output to `OutputCapabilities`.

Speech:

- `cancel_speech()` calls `outputs.speech.cancel()`.
- `speak(items)` wraps strings in `SpeechSequence`.
- Empty strings are removed before speaking.

Tone:

- If `outputs.tone` exists, failure beep uses that tone output.
- If `outputs.tone` is absent, failure beep is a no-op.
- A no-op beep must not cause command handling to fail.

The original NVDA `BreakCommand(1)` pauses are not required for the first migration. If speech becomes too dense, a later implementation can add a repository-native speech pause command or chunking strategy.

## 9. Error Handling

File selection:

- The file picker filters to `.graphml`.
- The controller stores a selected path only if it exists and has `.graphml` suffix.

Start navigation:

- If no file is selected, the controller raises a clear validation error and leaves the app idle.
- If parser or model construction fails, the controller reports the exception message to the UI and leaves keyboard capture inactive.
- If keyboard capture activation fails, the controller rolls back to idle and reports the activation error.

During navigation:

- Unknown commands are treated as handled with no state transition.
- State methods returning false trigger failure beep.
- Flow errors are caught at the service boundary, reported through status notification, and navigation is stopped to avoid trapping all keyboard input in a broken state.

Shutdown:

- Stop navigation if active.
- Stop input and hotkey capture if running.
- Shut down speech output.

## 10. Testing Strategy

Unit tests:

- `Access8GraphKeyTranslator` maps arrows, Enter, Escape, Home/End, and MRT letter keys correctly.
- Unsupported keys return no command.
- Flow output adapter calls cancel and speak in order.
- Flow startup speaks the mode menu without NVDA imports.
- Service cannot start without a selected file.
- Service reports parse/model errors without starting keyboard capture.
- Service returns `KeyboardPipelineResult(send_to_system=False, app_result=HANDLED_STOP)` while navigation is active.
- Escape stops navigation.

Integration tests:

- Load a small existing Access8Graph `.graphml` fixture.
- Build `Graph -> MrtModel -> MrtDirectionNavigator/MrtUndirectionNavigator -> MrtFlow`.
- Verify initial mode menu speech is emitted.
- Drive a short sequence such as Down, Enter, or direction mode selection against fake output.

UI tests:

- Main frame starts with `Start Navigation` disabled.
- Choosing a `.graphml` path updates status and enables start.
- Start/stop button labels reflect controller status notifications.
- Close hides the frame instead of exiting, matching `key_echo`.

Manual verification:

- Run `PYTHONPATH=src python -m apps.access8graph.main`.
- Choose a known `.graphml` file.
- Start navigation.
- Confirm speech announces the mode menu.
- Use arrows and Enter to navigate lists.
- Use Escape or Stop Navigation to return to idle.
- Open speech settings from tray and verify backend controls still work.

## 11. Rollout

Implementation should proceed in small steps:

1. Copy and de-NVDA the GraphML parser/model/navigator modules.
2. Extract and adapt MRT flow output/failure behavior.
3. Add key translator and service tests.
4. Add Access8Graph app runtime and GUI.
5. Wire tray and shared speech settings.
6. Run targeted unit tests, then the full test suite.

This keeps the pure parser/model work independent from GUI and keyboard capture integration.

## 12. Confirmed Decisions

- The first-stage file picker supports only `.graphml`.
- The first-stage app is GUI-based, not CLI-only.
- The first-stage migration is MRT-only and excludes generic directed graph navigation.
- The first-stage runtime does not implement NVDA review text or Explorer selected-file integration.
