import sys
import time
from multiprocessing import Process

import cv2
import numpy as np
from PyQt5.QtGui import QIcon, QImage, QPixmap
from PyQt5.QtWidgets import QApplication

from .QtWindows import App


class Viewer(Process):
    def __init__(self, Button_num, client_server):
        Process.__init__(self)
        self.in_pipes = None
        self.status_dict = None
        self.info_pipe = None
        self.img_map = None
        self.infer_mask = None
        self.camera_groups = None
        self.no_show_flag = None

        self.client_server = client_server
        self.Button_num = Button_num

    def set_pipe(self, in_pipes=None):
        self.in_pipes = in_pipes

    def set_status_dict(self, status_dict=None, infer_mask=None, camera_groups=None, no_show_flag=None):
        self.status_dict = status_dict
        self.img_map = None
        self.infer_mask = infer_mask
        self.camera_groups = camera_groups
        self.no_show_flag = no_show_flag

    def process_imgs(self, imgs):
        img_num = len(imgs)
        line_num = 3
        big_imgs = []

        for i in range(line_num):
            start_index = img_num // 3 * i
            end_index = img_num // 3 * i + img_num // 3
            one_line_imgs = imgs[start_index:end_index]

    def run(self):
        while True:
            if self.in_pipes is not None:
                break

        app = QApplication([])
        ex = App(self.Button_num, self.in_pipes, self.status_dict, self.img_map, self.infer_mask, self.camera_groups,
                 self.no_show_flag, self.client_server)
        sys.exit(app.exec_())

    def stop(self):
        self.terminate()
