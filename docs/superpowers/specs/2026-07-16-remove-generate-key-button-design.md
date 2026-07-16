# Remove Generate Key Button

## Scope

Remove the connection editor's key-generation UI and all code that exists only to support it.

## Design

In `src/ui/nvda_remote/connection_editor.py`, remove the `generate_key()` helper, the
`generate_button` control, its addition to the button row, its event binding, and the
`_on_generate_key()` handler. The dialog continues to expose the key text control for
manual entry and retains the OK and Cancel buttons.

Remove the unit test that exists solely for `generate_key()`. Keep all other connection
editor behavior and tests unchanged.

## Validation

Run the focused connection-editor UI tests, then run the complete unit and integration
test suite.
