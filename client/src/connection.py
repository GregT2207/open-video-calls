import datetime
import math
import random
import socket
import threading

import cv2
import numpy as np
from rtp import RTP


class Connection:
    SERVER_ADDRESS = "127.0.0.1"
    SERVER_PORT = 5000
    DEFAULT_COMPRESSED_QUALITY = 90
    RTP_MAX_PAYLOAD_BYTES = 1200
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
        if frame.size == 0:
            return

        compressed_frame = self.compress_frame(frame)
        fragments = self.get_fragments(compressed_frame)

        for index, fragment in enumerate(fragments):
            self.transmit_rtp_packet(
                bytearray(fragment.tobytes()), timestamp, index == (len(fragments) - 1)
            )

    def compress_frame(self, frame: np.ndarray) -> np.ndarray:
        # Determine quality based on current bandwidth

        _, compressed_frame = cv2.imencode(
            ".jpg",
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), self.DEFAULT_COMPRESSED_QUALITY],
        )
        print(
            f"Compressed frame from {frame.size * frame.itemsize / 1000} KB to {compressed_frame.size * compressed_frame.itemsize / 1000} KB"
        )

        return compressed_frame

    def get_fragments(self, frame: np.ndarray) -> np.ndarray:
        frame_bytes = frame.size * frame.itemsize
        fragment_count = math.ceil(frame_bytes / self.RTP_MAX_PAYLOAD_BYTES)
        print(
            f"Splitting {frame_bytes / 1000} KB frame into {fragment_count} fragments"
        )

        return np.array_split(frame, fragment_count, axis=0)

    def transmit_rtp_packet(self, payload: bytearray, timestamp: int, marker=False):
        rtp_packet = RTP(
            version=2,
            padding=False,
            marker=marker,
            sequenceNumber=self.seq,
            timestamp=self.get_timestamp(timestamp),
            ssrc=random.getrandbits(32),
        )

        rtp_packet.payload = payload
        print(f"Attached {len(payload)} B payload to RTP packet")

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
