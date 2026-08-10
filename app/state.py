class ReaderState:
    def __init__(self):
        self.is_running = False
        self.stop_requested = False

state = ReaderState()