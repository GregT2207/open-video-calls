import datetime
import math
import threading
import time

import cv2
import numpy as np


class View:
    WINDOW_NAME = "Chat"
    WINDOW_WIDTH = 1280
    WINDOW_HEIGHT = 720
    CONNECTION_EXPIRY_SECONDS = 5

    def __init__(self, call):
        self.call = call
        self.cam = cv2.VideoCapture(0)
        self.cam_frame = np.zeros((self.WINDOW_HEIGHT, self.WINDOW_WIDTH, 3))
        self.connection_frames: dict[int, np.ndarray] = {}

        cv2.namedWindow(self.WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.WINDOW_NAME, self.WINDOW_WIDTH, self.WINDOW_HEIGHT)
        cv2.moveWindow(self.WINDOW_NAME, 0, 0)

    def start(self) -> bool:
        print("Creating new view")

        remove_stale_frames_thread = threading.Thread(
            name="remove_stale_frames_thread",
            target=self.remove_stale_frames,
            daemon=True,
        )
        remove_stale_frames_thread.start()

        while self.call.running:
            self.read()
            self.draw()

            if cv2.waitKey(1) & 0xFF == 27:  # esc
                self.clean_up()

    def read(self):
        ret, self.cam_frame = self.cam.read()
        if not ret:
            print("Failed to read from camera")
            return

        self.call.connection.send_frame(self.cam_frame, datetime.datetime.now())

    def draw(self):
        image = np.zeros((self.WINDOW_HEIGHT, self.WINDOW_WIDTH, 3), dtype=np.uint8)

        image = self.draw_grid(image)
        image = self.draw_analytics(image)

        cv2.imshow(self.WINDOW_NAME, image)

    def draw_grid(self, image: np.ndarray) -> np.ndarray:
        user_frames: list[np.ndarray] = [
            self.cam_frame,
            *self.connection_frames.values(),
        ]

        grid_len = math.ceil(math.sqrt(len(user_frames)))

        view_width = int(self.WINDOW_WIDTH / grid_len)
        view_height = int(self.WINDOW_HEIGHT / grid_len)

        col, row = 0, 0
        for _, user_view in enumerate(user_frames):
            if user_view is None or user_view.size == 0:
                continue

            user_view = cv2.resize(
                user_view,
                (view_width, view_height),
            )

            y = view_height * row
            x = view_width * col

            image[y : y + view_height, x : x + view_width] = user_view

            if col == grid_len - 1:
                col = 0
                row += 1
            else:
                col += 1

        return image

    def draw_analytics(self, image: np.ndarray) -> np.ndarray:
        image = self.draw_analytics_text(
            image,
            f"Connected to {self.call.connection.SERVER_ADDRESS}:{self.call.connection.SERVER_PORT}",
            0,
        )
        image = self.draw_analytics_text(image, self.get_bitrate_text(), 1)
        image = self.draw_analytics_text(
            image,
            f"{str(round(self.call.connection.compression_quality))}% image quality",
            2,
        )

        return image

    def get_bitrate_text(self) -> str:
        bitrate = self.call.connection.bps
        thousands = 0

        while bitrate >= 1000 and thousands < 4:
            bitrate /= 1000
            thousands += 1

        thousands_text = {0: "Bps", 1: "Kbps", 2: "Mbps", 3: "Gbps", 4: "Tbps"}

        return str(round(bitrate)) + " " + thousands_text[thousands]

    def draw_analytics_text(
        self, image: np.ndarray, text: str, line: int
    ) -> np.ndarray:
        indent = (20, 40)
        line_gap = 35

        return cv2.putText(
            image,
            text,
            (indent[0], indent[1] + (line_gap * line)),
            cv2.QT_FONT_NORMAL,
            1,
            (255, 0, 0),
            2,
            cv2.LINE_AA,
            False,
        )

    def remove_stale_frames(self):
        while self.call.running:
            indexes_to_remove = list()

            prev_frames = self.connection_frames.copy()
            time.sleep(self.CONNECTION_EXPIRY_SECONDS)
            for index, frame in self.connection_frames.items():
                if index in prev_frames and np.array_equal(frame, prev_frames[index]):
                    indexes_to_remove.append(index)

            for index in indexes_to_remove:
                del self.connection_frames[index]

    def clean_up(self):
        print("Cleaning up view resources and ending call")

        self.cam.release()
        cv2.destroyAllWindows()
        self.call.running = False
