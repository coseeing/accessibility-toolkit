from apps.nvda_remote.connections.links import format_connection_url
from apps.nvda_remote.connections.models import SavedConnection


def connection(**changes):
    values = dict(
        id="f30cbe12-d88e-4ce7-86c6-905274559839",
        name="Office",
        host="relay.example",
        port=6837,
        key="space & symbols",
        insecure=False,
    )
    values.update(changes)
    return SavedConnection(**values)


def test_link_omits_default_port_and_encodes_key():
    assert format_connection_url(connection()) == (
        "nvdaremote://relay.example?key=space+%26+symbols&mode=slave"
    )


def test_link_brackets_ipv6_and_includes_non_default_port_and_insecure():
    assert format_connection_url(connection(host="2001:db8::1", port=7000, insecure=True)) == (
        "nvdaremote://[2001:db8::1]:7000?key=space+%26+symbols&mode=slave&insecure=true"
    )
