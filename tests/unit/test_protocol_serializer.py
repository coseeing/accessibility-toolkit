from remote_core.protocol import RemoteMessageType
from remote_core.serializer import JSONSerializer


def test_serializer_imports_are_available():
    serializer = JSONSerializer()
    assert RemoteMessageType.KEY.value == "key"
    assert serializer.SEP == b"\n"
