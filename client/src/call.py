import threading

import cv2

from connection import Connection
from view import View


class Call:
    def __init__(self):
        self.running = True
        self.view = View(self)
        self.connection = Connection(self)

    def start(self):
        print("Joining call")

        connection_thread = threading.Thread(
            name="connection", target=self.connection.start, daemon=True
        )
        connection_thread.start()

        self.view.start()
