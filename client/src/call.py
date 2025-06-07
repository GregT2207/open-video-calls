import threading

import cv2
import numpy as np

from connection import Connection
from view import View


class Call:
    def __init__(self):
        self.cam = cv2.VideoCapture(0)
        self.get_cam_frame()
        self.view = View(self)
        self.connection = Connection(self)

    def start(self):
        self.view.start()
        self.connection.start()

        while True:
            self.get_cam_frame()

            if cv2.waitKey(1) & 0xFF == 27:  # esc
                break

        self.clean_up()

    def get_cam_frame(self):
        ret, self.cam_frame = self.cam.read()
        if not ret:
            print("Failed to read from camera")

    def clean_up(self):
        self.cam.release()
        cv2.destroyAllWindows()
