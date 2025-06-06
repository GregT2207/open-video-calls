import math

import cv2
import numpy as np


class Call:
    def __init__(self):
        self.window_name = "Chat"
        self.window_width = 1280
        self.window_height = 720

        self.cam = cv2.VideoCapture(0)

        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, self.window_width, self.window_height)

        while True:
            view = self.build_grid()
            cv2.imshow(self.window_name, view)

            if cv2.waitKey(1) & 0xFF == 27:  # esc
                break

        self.cam.release()
        cv2.destroyAllWindows()

    def build_grid(self) -> np.ndarray:
        user_views = [self.get_self_view(), *self.get_others_view()]
        grid_len = math.ceil(math.sqrt(len(user_views)))

        grid = np.zeros((self.window_height, self.window_width, 3), dtype=np.uint8)
        view_width = int(self.window_width / grid_len)
        view_height = int(self.window_height / grid_len)

        col, row = 0, 0
        for index, user_view in enumerate(user_views):
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

        return grid

    def get_self_view(self) -> np.ndarray:
        ret, frame = self.cam.read()
        if not ret:
            print("Failed to read from camera")
            return []

        return frame

    def get_others_view(self) -> list[np.ndarray]:
        test_img = cv2.imread("test.png")
        if test_img is None:
            print(f"Failed to load image from file {test_img}")
            return []

        return [
            test_img,
            test_img,
            test_img,
            test_img,
            test_img,
            test_img,
            test_img,
            test_img,
            test_img,
        ]
