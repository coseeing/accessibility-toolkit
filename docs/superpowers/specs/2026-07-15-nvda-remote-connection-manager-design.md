# NVDA Remote Connection Manager Design

## Goal

Bring Remote PlusPlus-style connection management to the standalone NVDA Remote
client. Users can save Relay connection details, organize them, and connect to
them quickly without requiring an NVDA runtime.

## Scope

The feature includes saved connections, groups, search, ordering, connection
links, a configurable quick-connect default, and a wxPython connection manager.

It deliberately excludes all NVDA-only concepts:

- leader/follower connection modes and reversed-mode connections;
- local/self-hosted control-server connections;
- automatic connection at application startup.

All saved entries represent an ordinary outgoing Relay connection.

## Architecture

Create an application-level connection-management module independent of wxPython
and the transport implementation. It contains validated saved-connection models,
a JSON-backed repository, and a service exposing connection and management
operations. The wxPython views use this service and do not access JSON directly.

`NvdaRemoteAppService` receives the management service and exposes operations to
connect a saved entry or the configured quick-connect default. Connecting a saved
entry while another session is active first performs the normal disconnect flow,
then starts the selected Relay connection.

The manager persists separately from speech preferences using the application's
existing runtime configuration location: the working directory in development
and the executable directory in a frozen build. Its filename is
`nvda_remote_connections.json`. Writes use a temporary sibling file followed by
`os.replace` so a failed write does not corrupt the active configuration.

## Data model and persistence

The JSON document contains:

- `format_version`: the integer `1`;
- `active_group`: the last selected group;
- `close_on_connect`: whether starting a connection without an immediate error
  closes the manager dialog;
- `quick_connect_id`: the saved connection ID used by the main-window quick
  connect action, or `null` when no default exists;
- `groups`: an ordered mapping from group names to ordered saved connections.

Each saved connection has a UUID `id`, non-empty display `name`, non-empty `host`,
integer `port` from 1 through 65535, non-empty `key`, and Boolean `insecure` for
opting out of TLS certificate validation. Connection IDs are globally unique
across all groups; a file containing duplicate IDs is invalid.

The initial document has the non-removable `Default` group, an empty connection
list, and no quick-connect default. Removing a non-default group moves all of its
connections to `Default`. Removing the quick-connect entry clears
`quick_connect_id` to `null`.

Connection keys are stored as plain text in the local runtime configuration file,
matching the Remote PlusPlus behavior. The configuration file is runtime data and
is not a repository artifact.

If the file cannot be parsed or does not validate, the application logs the
failure and continues with the untouched file and an in-memory empty default
document. It must not overwrite the unreadable file during load.

## Management operations

The manager supports creating, renaming, and deleting groups; listing groups;
remembering the active group; and moving a group's entries to `Default` when the
group is deleted. `Default` cannot be renamed or deleted. Group names are trimmed,
non-empty, and unique using case-sensitive comparison. The group manager supports
deleting multiple non-default groups in one confirmed action.

For connections it supports create, read, update, delete, and adjacent ordering
within the group, including deleting multiple selected entries in one confirmed
action. Search filters the selected group by case-insensitive name or host.
Reordering a filtered list swaps the underlying adjacent visible entries,
preserving the Remote PlusPlus behavior.

The user may designate any saved connection as the quick-connect default. Its
ID is persisted. If no default exists, or if it was deleted, quick connect is
unavailable.

The manager copies links using the established NVDA Remote URL format:
`nvdaremote://host[:port]?key=<url-encoded-key>&mode=slave`, with
`&insecure=true` appended only when certificate validation is disabled. IPv6
hosts use brackets and the default port 6837 is omitted. `mode=slave` is a fixed
compatibility detail for the peer receiving the link; connection mode is neither
stored nor editable in this client. A local formatter implements and tests this
format without depending on the NVDA-only `ConnectionInfo.getURLToConnect()` API.

## User interface

The main frame does not provide manual Host, Port, or Key connection fields.
Every connection target must first be created in the connection manager; users
then connect from the saved list or the configured quick-connect action. It adds:

- **Manage Connections**, which opens the connection-manager dialog;
- **Quick Connect**, which connects the configured default entry.

Quick Connect is disabled when `quick_connect_id` is null, stale, or while a
connection is connecting or connected. Manage Connections is disabled only while
a connection attempt is in progress and remains available while connected. This
allows the user to select another saved entry; doing so runs the normal disconnect
flow before connecting to the new target. The main frame also retains a dedicated
Disconnect action, disabled while idle. Deleting the default entry refreshes the
main frame and disables Quick Connect immediately.

The manager dialog provides group selection, group management, search, and a
connection list showing name, host, and port. It provides New, Edit, Delete, and
Close actions. Double-clicking an entry connects it. The dialog also supplies a
context menu and keyboard actions for edit, delete, copy link, set as quick
connect, and move up/down. It has a persisted **Close after connecting** option.
When enabled, this option closes only the manager dialog after a connection
attempt starts without an immediate error; it never closes the main application
window.

The connection editor validates required fields before saving. Invalid host/name/
key values and ports outside 1–65535 show an accessible wx error dialog and leave
the stored data unchanged. Name, host, and key are trimmed and must remain
non-empty; host and port are separate fields. The editor provides a Generate Key
action that uses a cryptographically secure generator to produce a seven-digit
decimal key. Connection failures use the application's existing error reporting;
TLS certificate failures may be retried with the entry's explicit `insecure`
setting only.

The connection-list keyboard actions match the applicable Remote PlusPlus
shortcuts: `Alt+Up` and `Alt+Down` reorder, `F2` edits, `Delete` deletes, `Ctrl+A`
selects all, and `Ctrl+C` copies a link when exactly one entry is selected. Plain
Enter or list activation connects. Reversed-mode `Shift+Enter` is excluded.

## Testing

Unit tests cover repository defaults, validation, CRUD, group movement,
searching, ordering, quick-connect assignment and clearing, atomic save, and
corrupt-file recovery. Service tests cover connecting saved entries, quick
connect, stale defaults, and replacement of an existing connection. wx tests
cover manager actions and the enabled state of Quick Connect and management
controls as saved/default/connection state changes.

The implementation is complete when the focused tests and the repository's full
`pytest tests/unit tests/integration -v` suite pass.
