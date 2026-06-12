from apps.shared.panel_controller import PanelController


class FakeFrame:
    def __init__(self):
        self.hidden = 0
        self.shown = 0
        self.raised = 0

    def Show(self, show=True):
        if show:
            self.shown += 1

    def Hide(self):
        self.hidden += 1

    def Raise(self):
        self.raised += 1


def test_show_panel_shows_and_raises_existing_frame():
    frame = FakeFrame()
    controller = PanelController()
    controller.register("main", frame)

    controller.show("main")

    assert frame.shown == 1
    assert frame.raised == 1


def test_close_handler_hides_panel_instead_of_exiting():
    frame = FakeFrame()
    controller = PanelController()
    controller.register("main", frame)

    controller.hide("main")

    assert frame.hidden == 1
