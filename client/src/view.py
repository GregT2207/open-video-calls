import math

import cv2
import numpy as np


class View:
    def __init__(self, call):
        self.call = call
        self.window_name = "Chat"
        self.window_width = 1280
        self.window_height = 720
        self.others = []

        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, self.window_width, self.window_height)

    def start(self) -> None:
        while True:
            user_frames = [self.call.cam_frame, *self.call.connection.frames]

            grid_len = math.ceil(math.sqrt(len(user_frames)))

            grid = np.zeros((self.window_height, self.window_width, 3), dtype=np.uint8)
            view_width = int(self.window_width / grid_len)
            view_height = int(self.window_height / grid_len)

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

            cv2.imshow(self.window_name, grid)
