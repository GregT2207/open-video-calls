import datetime
import random
import socket
import threading

import numpy as np
from rtp import RTP


class Connection:
    SERVER_ADDRESS = "127.0.0.1"
    SERVER_PORT = 5000
    RTP_TICK_RATE = 90_000

    def __init__(self, call):
        self.call = call

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setblocking(False)

        self.seq = random.getrandbits(16)
        self.timestamp_base = random.getrandbits(32)
        self.timestamp_initial = datetime.datetime.now()

    def start(self):
        print("Establishing connection with server")

        receiving_thread = threading.Thread(
            name="connection_receiving", target=self.start_receiving_frames
        )
        receiving_thread.start()

    def send_frame(self, frame: np.ndarray, timestamp: int):
        compressed_frame = self.compress_frame(frame)
        fragments = self.get_fragments(compressed_frame)

        for fragment in fragments:
            self.transmit_rtp_packet(bytearray(fragment.tobytes()), timestamp)

    def compress_frame(self, frame: np.ndarray) -> np.ndarray:
        # Determine bit-rate based on current bandwidth
        return frame

    def get_fragments(self, frame: np.ndarray) -> list[np.ndarray]:
        return [frame]

    def transmit_rtp_packet(self, payload: bytearray, timestamp: int):
        rtp_packet = RTP(
            version=2,
            padding=False,
            marker=False,
            sequenceNumber=self.seq,
            timestamp=self.get_timestamp(timestamp),
            ssrc=random.getrandbits(32),
        )
        rtp_packet.payload = payload

        self.socket.sendto(
            rtp_packet.toBytearray(), (self.SERVER_ADDRESS, self.SERVER_PORT)
        )

        self.seq = (self.seq + 1) & 0xFFFF

    def get_timestamp(self, timestamp: datetime.datetime) -> int:
        delta = timestamp - self.timestamp_initial
        ticks = int(delta.total_seconds() * self.RTP_TICK_RATE)

        return ticks & 0xFFFFFFFF

    def start_receiving_frames(self):
        print("Beginning receipt of data")

        # self.socket.bind((self.SERVER_ADDRESS, self.SERVER_PORT))
        # while self.call.running:
        #     data, address = socket.recvfrom(1024)
        #     print(f"Received message {data}")
