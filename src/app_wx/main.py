from adapters.windows.clipboard import WindowsClipboardService
from adapters.windows.keyboard_hook import WindowsKeyboardCapture
from adapters.windows.nvda_controller import NvdaControllerSpeechOutput
from app_wx.app import NvdaRemoteApp
from application.controller import ClientController
from remote_core.serializer import JSONSerializer
from remote_core.transport.relay import RelayTransport


def main() -> int:
    controller = ClientController(
        transport=RelayTransport(JSONSerializer()),
        input_capture=WindowsKeyboardCapture(),
        clipboard=WindowsClipboardService(),
        speech_output=NvdaControllerSpeechOutput.load_default(),
    )
    app = NvdaRemoteApp(controller=controller)
    return app.MainLoop()


if __name__ == "__main__":
    raise SystemExit(main())
