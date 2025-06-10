import datetime
import math
import random
import socket
import threading
import time

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

        self.buffers: dict[int, dict[int, RTP]] = {}  # [ssrc: [seq: packet]]
        self.ssrc = random.getrandbits(32)
        self.seq = random.getrandbits(16)
        self.timestamp_initial = datetime.datetime.now()
        self.timestamp_base = random.getrandbits(32)
        self.connection_id = random.getrandbits(32)

    def start(self):
        self.socket.bind(("", 0))
        print(
            f"Communicating with {self.SERVER_ADDRESS}:{self.SERVER_PORT} through local port {self.socket.getsockname()[1]}"
        )

        receive_packets_thread = threading.Thread(
            name="connection_receive_packets",
            target=self.receive_packets,
            daemon=True,
        )
        receive_packets_thread.start()

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
        if self.call.debug:
            print(
                f"Compressed frame from {frame.size * frame.itemsize / 1000} KB to {compressed_frame.size * compressed_frame.itemsize / 1000} KB"
            )

        return compressed_frame

    def get_fragments(self, frame: np.ndarray) -> np.ndarray:
        frame_bytes = frame.size * frame.itemsize
        fragment_count = math.ceil(frame_bytes / self.RTP_MAX_PAYLOAD_BYTES)
        if self.call.debug:
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
            ssrc=self.ssrc,
        )

        rtp_packet.payload = payload
        if self.call.debug:
            print(f"Attached {len(payload)} B payload to RTP packet")

        self.socket.sendto(
            rtp_packet.toBytearray(), (self.SERVER_ADDRESS, self.SERVER_PORT)
        )

        self.seq = (self.seq + 1) & 0xFFFF

    def get_timestamp(self, timestamp: datetime.datetime) -> int:
        delta = timestamp - self.timestamp_initial
        ticks = int(delta.total_seconds() * self.RTP_TICK_RATE)

        return ticks & 0xFFFFFFFF

    def receive_packets(self):
        while self.call.running:
            data, address = self.socket.recvfrom(1500)
            if address[0] != self.SERVER_ADDRESS:
                print(f"Ignoring data received from unexpected address: {address}")
                continue

            rtp_packet = RTP().fromBytes(data)

            if rtp_packet.marker:
                assemble_frame_thread = threading.Thread(
                    name="connection_assemble_frame",
                    target=self.assemble_frame,
                    args=(rtp_packet.ssrc,),
                    daemon=True,
                )
                assemble_frame_thread.start()

            if rtp_packet.ssrc not in self.buffers:
                self.buffers[rtp_packet.ssrc] = {}
            self.buffers[rtp_packet.ssrc][rtp_packet.sequenceNumber] = rtp_packet

    def assemble_frame(self, ssrc: int):
        frame = np.concatenate(*self.get_frame_packets(ssrc))
        self.call.view.connection_frames[ssrc] = frame

    def get_frame_packets(self, ssrc: int) -> list[np.ndarray]:
        data: list[np.ndarray] = list()

        next_seq = next(iter(self.buffers[ssrc]))
        for _ in range(5):
            while next_seq in self.buffers[ssrc]:
                next_packet = self.buffers[ssrc].pop(next_seq)
                data.append(next_packet.payload.decode())

                if next_packet.marker:
                    return data

                next_seq += 1

            time.sleep(0.1)

        return data
