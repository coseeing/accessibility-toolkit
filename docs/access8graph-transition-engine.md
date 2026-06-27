# Access8Graph Transition Engine Extension Guide

How to extend the navigation state machine with new states, commands, guards,
actions, and rules.  Follow these steps in order.

---

## 1. Add a `NavigationCommand` or `NavigationStateId` enum member

Open `src/apps/access8graph/navigation/model.py` and add your member to the
appropriate `StrEnum`:

```python
class NavigationCommand(StrEnum):
    # ... existing members ...
    MY_NEW_COMMAND = "my_new_command"

class NavigationStateId(StrEnum):
    # ... existing members ...
    MY_NEW_STATE = "my_new_state"
```

The `StrEnum` value is the canonical string used throughout rules, guards, and
actions.

---

## 2. Add snapshot facts (only when a pure guard requires them)

Open `src/apps/access8graph/navigation/snapshot.py`.  Guards are pure
functions that receive a `NavigationSnapshot` and return `bool`.  If your new
guard needs a fact not already present on the snapshot, add a new field:

```python
@dataclass(frozen=True, slots=True)
class NavigationSnapshot:
    # ... existing fields ...
    my_new_fact: bool = False
```

Then update `NavigationSnapshotFactory.create` to accept and forward the new
field.  The factory is called by `build_snapshot_factory()` in
`src/apps/access8graph/navigation/actions.py` — wire the real data source
there.

> Only add fields that guards actually read.  Do not bloat the snapshot.

---

## 3. Register a pure guard for each mutually exclusive data branch

Each guard is a callable `(NavigationSnapshot) -> bool`.  Guard IDs are
defined via `GuardId("guard_name")`.

### Declare the guard ID constant

In `src/apps/access8graph/navigation/actions.py`, add to the top-level
constants:

```python
G_MY_CONDITION = GuardId("my_condition")
G_NOT_MY_CONDITION = GuardId("not_my_condition")
```

Add both to `ALL_GUARD_IDS`:

```python
ALL_GUARD_IDS: frozenset[GuardId] = frozenset({
    # ... existing entries ...
    G_MY_CONDITION,
    G_NOT_MY_CONDITION,
})
```

### Implement the guard function

In `build_guard_registry()`, register each guard with its decision logic.
The guard reads from `NavigationSnapshot` only — never mutates context:

```python
def _my_condition_enabled(snapshot: NavigationSnapshot) -> bool:
    return snapshot.my_new_fact


def _my_condition_disabled(snapshot: NavigationSnapshot) -> bool:
    return not snapshot.my_new_fact
```

> Every data branch must have exactly one guard.  If a rule has no guard
> (`guard_id=None`) it always matches and must be the only rule for its
> `(source, command)` key.

---

## 4. Register an action (validate before mutation, never select target)

Actions receive `(NavigationSnapshot, NavigationContext)` and return an
`ActionResult`.  They must **validate** preconditions and mutate only the
`NavigationContext.view_model` (or other mutable fields).  They must **never**
change `context.current_state` — the engine commits the target after the
action succeeds.

### Declare the action ID constant

```python
A_MY_ACTION = ActionId("my_action")
```

Add it to `ALL_ACTION_IDS`.

### Implement the action

In `build_action_registry()`:

```python
def my_action(snapshot: NavigationSnapshot, context: NavigationContext) -> ActionResult:
    # 1. Validate preconditions
    if not context.view_model:
        return ActionResult.rejected()

    # 2. Mutate view_model or context as needed
    context.view_model.selected_id = snapshot.selected_id

    # 3. Return accepted with optional presentation effects
    return ActionResult.accepted_with(
        effects=PresentationEffects(
            close_messages=("closed",),
            open_messages=("Hello, new state",),
            hints=("Press DOWN for more options",),
            view_items=(context.view_model.label,),
        )
    )
```

> Return `ActionResult.rejected()` to reject the transition without changing
> state.  The engine stays in the current state and delivers any effects in
> the rejected result.

---

## 5. Add fixed-target rules in the appropriate family table

Rules go in `src/apps/access8graph/navigation/table.py` inside
`build_transition_rules()`.

### Fixed-target guarded example

Two rules for the same `(source, command)` key using mutually exclusive
guards:

```python
MY_S = NavigationStateId.MY_NEW_STATE

rules.append(_r(
    NavigationStateId.MODE,
    NavigationCommand.MY_NEW_COMMAND,
    NavigationStateId.STATIONS,
    A_MY_ACTION,
    G_MY_CONDITION,
))

rules.append(_r(
    NavigationStateId.MODE,
    NavigationCommand.MY_NEW_COMMAND,
    NavigationStateId.LINES,
    A_MY_ACTION,
    G_NOT_MY_CONDITION,
))
```

### AUTO example

An AUTO rule fires immediately after the parent transition completes, without
waiting for user input.  Use it to skip intermediate states:

```python
rules.append(_r(
    NavigationStateId.DIRECTION_LINES,
    NavigationCommand.AUTO,
    NavigationStateId.DIRECTION_STATIONS,
    A_DIRECTION_LINES_AUTO,
    G_HAS_ONE_OPTION,
))
```

When a `CONFIRM` action lands on `DIRECTION_LINES`, the engine checks for
`AUTO` rules.  If there is exactly one station (`G_HAS_ONE_OPTION` returns
`True`), the engine automatically transitions to `DIRECTION_STATIONS` without
presenting the intermediate `DIRECTION_LINES` state.

AUTO rules follow the same guard/action semantics as external commands.  The
engine runs AUTO steps in a loop (max 32 steps) and merges all presentation
effects into a single result.

---

## 6. Add lifecycle presentation without state mutation

Entry and exit effects fire when the engine commits a state change.  They
return `PresentationEffects` only — the engine re-affirms
`context.current_state` after running them to prevent accidental mutation.

### Register entry/exit effects

In `src/apps/access8graph/navigation/actions.py`, inside
`build_entry_effects()` and `build_exit_effects()`:

```python
def my_state_entry(snapshot: NavigationSnapshot, context: NavigationContext) -> PresentationEffects:
    return PresentationEffects(
        open_messages=("Entering my state",),
        hints=("Press CONFIRM to proceed",),
        view_items=(),
    )

# In build_entry_effects():
entry_effects[NavigationStateId.MY_NEW_STATE] = my_state_entry
```

---

## 7. Add characterization / contract tests

### Validator test

In `tests/unit/test_access8graph_transition_table.py`, add a case to
`INVALID_CASES` if your new rules can produce a validation error, or add a
positive test confirming the table validates.

### Transition engine test

In `tests/unit/test_access8graph_transition_engine.py`, test that:
- The correct guard wins when data matches.
- `AmbiguousTransitionError` is raised when two guards match.
- Actions that reject do not change state.
- AUTO chains advance correctly.

### Parity / flow test

In `tests/unit/test_access8graph_transition_parity.py` or
`tests/integration/test_access8graph_mrt_flow.py`, add a scenario that walks
through the new path end-to-end with a `FakeOutput` and asserts the expected
presentation sequence.

---

## 8. Run the verification suites

```bash
# Validator tests
.venv/bin/python -m pytest tests/unit/test_access8graph_transition_table.py -q

# Transition engine tests
.venv/bin/python -m pytest tests/unit/test_access8graph_transition_engine.py -q

# Access8Graph integration flow
.venv/bin/python -m pytest tests/integration/test_access8graph_mrt_flow.py -q

# Full parity suite
.venv/bin/python -m pytest tests/unit/test_access8graph_transition_parity.py -q

# Entire test suite
.venv/bin/python -m pytest -q
```

All suites must pass before merging.

---

## Summary checklist

- [ ] `NavigationCommand` or `NavigationStateId` enum member added
- [ ] Snapshot fields added **only if needed** by a pure guard
- [ ] `GuardId` constants declared and added to `ALL_GUARD_IDS`
- [ ] Guard functions registered in `build_guard_registry()` — one per data branch
- [ ] `ActionId` constant declared and added to `ALL_ACTION_IDS`
- [ ] Action registered in `build_action_registry()` — validates, mutates view model, never selects target
- [ ] Fixed-target rules (with guards) added to `build_transition_rules()`
- [ ] AUTO rules added for skip-ahead paths where appropriate
- [ ] Entry/exit effects registered for lifecycle presentation
- [ ] Characterization tests added for table validation and engine behavior
- [ ] All validator, transition, Access8Graph, and full suites pass
