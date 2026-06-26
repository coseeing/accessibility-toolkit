class RemoteStatusPresenter:
    def __init__(self, *, dispatch, get_listener) -> None:
        self._dispatch = dispatch
        self._get_listener = get_listener

    def notify(self, event) -> None:
        listener = self._get_listener()
        if listener is None:
            return
        self._dispatch(lambda: listener(event))
