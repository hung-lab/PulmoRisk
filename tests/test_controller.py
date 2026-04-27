from app.controllers.app_controller import AppController


class FakeView:
    def __init__(self):
        self.status = None

    def update_status(self, msg):
        self.status = msg


def test_button_click_updates_view():
    controller = AppController(root=None)

    fake_view = FakeView()
    controller.set_view(fake_view)

    controller.on_button_click()

    assert fake_view.status == "Button clicked!"
