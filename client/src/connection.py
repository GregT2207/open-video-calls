import socket

import numpy as np


class Connection:
    SERVER_ADDRESS = "127.0.0.1"
    SERVER_PORT = "5000"
    FPS = 30

    def __init__(self, call):
        self.call = call
        self.frames: list[np.ndarray] = []
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def start(self):
        while True:
            self.frames = []
