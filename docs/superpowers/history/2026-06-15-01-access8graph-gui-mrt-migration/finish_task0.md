# Access8Graph GUI MRT Migration - Implementation Complete

## Summary

Access8Graph GUI MRT migration successfully implemented. All 8 tasks from the plan are complete. The migration copies the pure GraphML/MRT parser and navigator from the original NVDA add-on, adapts the MRT flow state machine to use explicit output callbacks, and wires everything through a `key_echo`-style wxPython GUI with shared tray and speech settings.

## Test Results

- **Access8Graph focused tests:** 42/42 passed
- **Related existing app tests (key_echo, tool_shell, speech_settings):** 33/33 passed
- **Full test suite:** 420/420 passed
- **Import smoke check:** `PYTHONPATH=src python3 -c "import apps.access8graph.main"` - OK

## Commits (8 commits)

```
82f981e fix: correct datas variable name in transfer_display
1a6de69 feat: add access8graph gui runtime
f8c7c8e feat: add access8graph app service
db51504 test: cover access8graph mrt flow smoke path
dcafe77 feat: port access8graph mrt flow
adea131 feat: add access8graph flow output adapter
d4054bf feat: add access8graph key translator
4163258 feat: migrate access8graph graphml core
```

## Files Created

### Application Layer (`src/apps/access8graph/`)
| File | Purpose |
|------|---------|
| `__init__.py` | Package marker |
| `main.py` | Runtime builder, mirroring `apps.key_echo.main` |
| `service.py` | App controller with file selection, navigation lifecycle, key pipeline, speech settings proxy |
| `input.py` | HID `KeyEvent` to Access8Graph command translator |
| `output.py` | `OutputCapabilities` adapter for flow speech/beep |
| `flow.py` | De-NVDA MRT flow state machine (24+ state classes) |
| `graphml/__init__.py` | GraphML package exports (Graph, MrtModel, navigators) |
| `graphml/model.py` | Migrated GraphML parser (Node, Edge, Graph, Path) |
| `graphml/mrt_model.py` | Migrated MRT model (stations, lines, transfers, routing) |
| `graphml/mrt_navigator.py` | Migrated MRT navigators (direction, undirection) |

### UI Layer (`src/ui/access8graph/`)
| File | Purpose |
|------|---------|
| `__init__.py` | Package marker |
| `app.py` | wx app shell using `ToolAppShell` |
| `main_frame.py` | Main frame with file picker, status, start/stop button |

### Tests
| File | Type | Count |
|------|------|-------|
| `tests/unit/test_access8graph_graphml.py` | Unit | 3 |
| `tests/unit/test_access8graph_input.py` | Unit | 22 |
| `tests/unit/test_access8graph_output.py` | Unit | 5 |
| `tests/unit/test_access8graph_flow.py` | Unit | 3 |
| `tests/unit/test_access8graph_app_service.py` | Unit | 5 |
| `tests/unit/test_access8graph_ui.py` | Unit | 3 |
| `tests/integration/test_access8graph_mrt_flow.py` | Integration | 1 |

## Key Adaptation Decisions

1. **Fixture path:** The plan's specified `graph.graphml` is a flat graph without `::`-separated node IDs. Used `Access8Graph/tests/test.graphml` instead, which has proper `y:ProxyAutoBoundsNode` containers and works with the MRT model.
2. **Flow output:** Replaced NVDA `speech.speak()` / `tones.beep()` with adapter callbacks (`cancel_speech()`, `speak()`, `beep_failure()`) using `OutputCapabilities`.
3. **Window lifecycle:** Removed all NVDA `Window` event methods (`event_gainFocus`, `event_loseFocus`, `setFocus`, `exit`).
4. **Translation fallback:** Added `_ = lambda m: m` fallback for `gettext` calls that exist in NVDA but not in standalone Python.

## Bug Fixed During Verification

- `mrt_navigator.py:398`: `data = []` corrected to `datas = []` (variable name mismatch in `transfer_display` except handler)

## Manual Launch

```bash
PYTHONPATH=src python -m apps.access8graph.main
```

Requires a desktop environment with wxPython support. In headless environments, the import check passes but the app cannot create a display.
