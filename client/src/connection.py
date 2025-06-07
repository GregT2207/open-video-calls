import socket
import threading
import time

import numpy as np


class Connection:
    SERVER_ADDRESS = "127.0.0.1"
    SERVER_PORT = 5000
    SEND_RATE = 30

    def __init__(self, call):
        self.call = call
        self.frames: list[np.ndarray] = []
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setblocking(False)

    def start(self):
        print("Establishing connection with server")

        sending_thread = threading.Thread(target=self.start_sending)
        receiving_thread = threading.Thread(target=self.start_receiving)

        sending_thread.start()
        receiving_thread.start()

    def start_sending(self):
        print("Beginning transmission of data")

        while self.call.running:
            self.socket.sendto(b"TEST", (self.SERVER_ADDRESS, self.SERVER_PORT))
            time.sleep(1 / self.SEND_RATE)

    def start_receiving(self):
        print("Beginning receipt of data")

        self.socket.bind((self.SERVER_ADDRESS, self.SERVER_PORT))
        while self.call.running:
            data, address = socket.recvfrom(1024)
            print(f"Received message {data}")
