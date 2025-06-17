import datetime
import math
import random
import socket
import threading
import time
from collections import deque

import cv2
import numpy as np
from rtp import RTP


class Connection:
    SERVER_ADDRESS = "127.0.0.1"
    SERVER_PORT = 5000
    DEFAULT_COMPRESSION_QUALITY = 80
    MIN_COMPRESSION_QUALITY = 20
    MAX_COMPRESSION_QUALITY = 100
    SMOOTHING_COMPRESSION_FACTOR = 0.1
    RTP_MAX_PAYLOAD_BYTES = 1200
    RTP_TICK_RATE = 90_000
    CONSUME_FPS = 30
    ADAPT_FRAME_QUALITY_FREQUENCY_SECONDS = 1

    def __init__(self, call):
        self.call = call

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.compression_quality = self.DEFAULT_COMPRESSION_QUALITY
        self.bytes_received = 0
        self.bps = 0

        self.ssrc = random.getrandbits(32)
        self.seq = random.getrandbits(16)
        self.timestamp_initial = datetime.datetime.now()
        self.timestamp_base = random.getrandbits(32)
        self.connection_id = random.getrandbits(32)

        self.packet_buffers: dict[int, dict[int, RTP]] = {}  # [ssrc: [seq: packet]]
        self.frame_buffers: dict[int, deque[tuple[int, np.ndarray]]] = (
            {}
        )  # [ssrc: (timestamp, queue[frame])]
        self.latest_timestamps: dict[int, int] = {}  # [ssrc: timestamp]

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

        consume_frame_buffer_thread = threading.Thread(
            name="connection_consume_frame_buffer",
            target=self.consume_frame_buffer,
            daemon=True,
        )
        consume_frame_buffer_thread.start()

        adapt_frame_quality_thread = threading.Thread(
            name="connection_adapt_frame_quality",
            target=self.adapt_frame_quality,
            daemon=True,
        )
        adapt_frame_quality_thread.start()

    def send_frame(self, frame: np.ndarray, timestamp: int):
        if frame.size == 0:
            return

        compressed_frame = self.compress_frame(frame)
        fragments = self.get_fragments(compressed_frame)

        for index, fragment in enumerate(fragments):
            self.transmit_rtp_packet(
                bytearray(fragment.tobytes()), timestamp, index == (len(fragments) - 1)
            )

    def lerp(a: float, b: float, t: float):
        t = max(0.0, min(1.0, t))
        result = a + (b - a) * t

        return result

    def adapt_frame_quality(self):
        while self.call.running:
            bytes_received_a = self.bytes_received
            time.sleep(self.ADAPT_FRAME_QUALITY_FREQUENCY_SECONDS)
            bytes_received_b = self.bytes_received

            new_bps = (
                bytes_received_b - bytes_received_a
            ) / self.ADAPT_FRAME_QUALITY_FREQUENCY_SECONDS

            target_compression_quality = (
                self.MAX_COMPRESSION_QUALITY
                if new_bps >= self.bps
                else self.MIN_COMPRESSION_QUALITY
            )

            new_compression_quality = Connection.lerp(
                self.compression_quality,
                target_compression_quality,
                self.SMOOTHING_COMPRESSION_FACTOR,
            )

            self.bps = new_bps
            self.compression_quality = new_compression_quality

    def compress_frame(self, frame: np.ndarray) -> np.ndarray:
        _, compressed_frame = cv2.imencode(
            ".jpg",
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), round(self.compression_quality)],
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
            self.bytes_received += len(data) * 8

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

            if rtp_packet.ssrc not in self.packet_buffers:
                self.packet_buffers[rtp_packet.ssrc] = {}
            self.packet_buffers[rtp_packet.ssrc][rtp_packet.sequenceNumber] = rtp_packet

    def assemble_frame(self, ssrc: int):
        timestamp, packets = self.get_frame_packets(ssrc)

        frame = np.concatenate(packets, axis=0)
        decoded_frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
        if decoded_frame is None:
            return

        if ssrc not in self.frame_buffers:
            self.frame_buffers[ssrc] = deque()
        self.frame_buffers[ssrc].append((timestamp, decoded_frame))

    def get_frame_packets(self, ssrc: int) -> tuple[int, list[np.ndarray]]:
        data: list[np.ndarray] = list()

        timestamp = 0
        next_seq = next(iter(self.packet_buffers[ssrc]))
        for _ in range(5):
            while next_seq in self.packet_buffers[ssrc]:
                next_packet = self.packet_buffers[ssrc].pop(next_seq)
                data.append(np.frombuffer(next_packet.payload, dtype=np.uint8))

                if next_packet.marker:
                    timestamp = next_packet.timestamp
                    return (timestamp, data)

                next_seq += 1

            time.sleep(0.1)

        return (timestamp, data)

    def consume_frame_buffer(self):
        next_frame_time = datetime.datetime.now()

        while self.call.running:
            time_to_next_frame = (
                next_frame_time - datetime.datetime.now()
            ).total_seconds()
            if time_to_next_frame > 0:
                time.sleep(time_to_next_frame)

            for ssrc, buffer in self.frame_buffers.items():
                if len(buffer) == 0:
                    continue

                timestamp, frame = buffer.popleft()

                if ssrc not in self.latest_timestamps:
                    self.latest_timestamps[ssrc] = 0

                # Drop any late frames
                if timestamp < self.latest_timestamps[ssrc]:
                    continue

                self.call.view.connection_frames[ssrc] = frame

            next_frame_time += datetime.timedelta(seconds=(1 / self.CONSUME_FPS))
