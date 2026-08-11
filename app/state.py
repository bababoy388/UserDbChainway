class ReaderState:
    def __init__(self):
        self.is_running = False
        self.stop_requested = False
        self.last_reader_data = None

state = ReaderState()