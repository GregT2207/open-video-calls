import datetime
import math
import threading

import cv2
import numpy as np


class View:
    WINDOW_NAME = "Chat"
    WINDOW_WIDTH = 1280
    WINDOW_HEIGHT = 720

    def __init__(self, call):
        self.call = call
        self.cam = cv2.VideoCapture(0)
        self.cam_frame = np.zeros((self.WINDOW_HEIGHT, self.WINDOW_WIDTH, 3))
        self.connection_frames: list[np.ndarray] = list()

        cv2.namedWindow(self.WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.WINDOW_NAME, self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

    def start(self) -> bool:
        print("Creating new view")

        while self.call.running:
            self.read()
            self.draw()

            if cv2.waitKey(1) & 0xFF == 27:  # esc
                self.end_call()

    def read(self):
        ret, self.cam_frame = self.cam.read()
        if not ret:
            print("Failed to read from camera")
            return

        self.call.connection.send_frame(self.cam_frame, datetime.datetime.now())

    def draw(self):
        user_frames = [self.cam_frame, *self.connection_frames]

        grid_len = math.ceil(math.sqrt(len(user_frames)))

        grid = np.zeros((self.WINDOW_HEIGHT, self.WINDOW_WIDTH, 3), dtype=np.uint8)
        view_width = int(self.WINDOW_WIDTH / grid_len)
        view_height = int(self.WINDOW_HEIGHT / grid_len)

        col, row = 0, 0
        for index, user_view in enumerate(user_frames):
            user_view = cv2.resize(
                user_view,
                (view_width, view_height),
            )

            y = view_height * row
            x = view_width * col

            grid[y : y + view_height, x : x + view_width] = user_view

            if col == grid_len - 1:
                col = 0
                row += 1
            else:
                col += 1

        cv2.imshow(self.WINDOW_NAME, grid)

    def end_call(self):
        print("Cleaning up view resources and ending call")

        self.cam.release()
        cv2.destroyAllWindows()
        self.call.running = False
