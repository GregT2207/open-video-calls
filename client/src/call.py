import threading

import cv2

from connection import Connection
from view import View


class Call:
    def __init__(self):
        self.running = True
        self.debug = False
        self.view = View(self)
        self.connection = Connection(self)

    def start(self):
        print("Joining call")

        self.connection.start()
        self.view.start()
