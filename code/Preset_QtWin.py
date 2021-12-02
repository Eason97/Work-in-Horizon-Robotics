# -*- coding: UTF-8 -*-
import os
import sys
import time
from functools import partial
from multiprocessing import Process

import cv2
import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import QRect, QSize, Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QIcon, QImage, QPixmap
# import PyQt5 as Qt
from PyQt5.QtWidgets import (QAction, QApplication, QCheckBox, QComboBox,
                             QDesktopWidget, QGridLayout, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit, QMainWindow,
                             QPushButton, QScrollArea, QTabWidget,
                             QTextBrowser, QVBoxLayout, QWidget)


class PreSetApp(QMainWindow):
    def __init__(self, camera_groups=None, camera_num=None):
        super().__init__()

        self.camera_groups = camera_groups
        self.camera_num = camera_num
        self.title = "摄像头选择"

        self.left = 0
        self.top = 0
        self.width = 1060
        self.height = 600

        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.table_widget = PresetTableWidget(self, self.camera_groups, self.camera_num)

        self.setCentralWidget(self.table_widget)
        # self.setStyleSheet("background-color: rgb(255, 255, 255)")
        self.show()
        self.setWindowState(Qt.WindowMaximized)

    def closeEvent(self, event):
        # print('select finish')
        event.accept()


class ClickedQLabel(QLabel):
    button_clicked_signal = pyqtSignal()

    def __init__(self, *__args):
        super(ClickedQLabel, self).__init__(*__args)

    def mouseReleaseEvent(self, QMouseEvent):
        self.button_clicked_signal.emit()

    def connect_customized_slot(self, func):
        self.button_clicked_signal.connect(func)


class PresetTableWidget(QWidget):
    def __init__(self, parent, camera_groups, camera_num):
        super(QWidget, self).__init__(parent)

        # self.layout = QVBoxLayout(self)

        self.camera_groups = camera_groups
        self.img_num = camera_num
        self.select_flag = []
        self.camera_name = []
        self.camera_id = 0
        self.other_camera_id = 0

        self.img_show_size = (640, 480)

        # self.tab = QWidget()
        # self.tab.resize(960, 640)

        # Create first tab
        self.layout = QVBoxLayout(self)
        self.tab = QWidget()
        self.setMinimumHeight(150)
        self.Hlayout = QHBoxLayout(self.tab)

        # self.buttons = []
        # self.textBrowsers = []

        order_text = QLabel('选择顺序：', self)
        # order_text.move(500, 15)
        self.order_base_text = 'LeftUp,Left,Up,Mid,Down,Right,RightUp'
        self.order_input = QLineEdit(self)
        self.order_input.setText(self.order_base_text)
        # self.order_input.setGeometry(QRect(565, 10, 200, 23))
        self.order_input.setMinimumSize(400, 50)

        button = QPushButton("重新采样", self)
        # button.setStyleSheet("background-color: green")
        # button.setGeometry(QRect(800, 10, 75, 23))
        button.setMinimumSize(150, 50)
        button.clicked.connect(self.camera_sampling)
        # self.buttons.append(button)

        self.button_reset = QPushButton("完成选择", self)
        # self.button_reset.setStyleSheet("background-color: green")
        self.button_reset.clicked.connect(self.finish)
        # self.button_reset.setGeometry(QRect(910, 10, 75, 23))
        self.button_reset.setMinimumSize(150, 50)

        self.Hlayout.addStretch(15)
        self.Hlayout.addWidget(order_text)
        self.Hlayout.addWidget(self.order_input)
        self.Hlayout.addStretch(1)
        self.Hlayout.addWidget(button)
        self.Hlayout.addStretch(1)
        self.Hlayout.addWidget(self.button_reset)
        self.Hlayout.addStretch(1)

        # self.groupBox = QGroupBox("相机画面", self)
        # self.groupBox.setGeometry(QRect(10, 50, 1000, 510))

        self.scrollWidget = QWidget()
        self.scrollWidget.setMinimumSize(4000, 4000)
        self.scroll = QScrollArea(self)
        # self.scroll.setGeometry(QRect(10, 50, 1020, 520))
        self.scroll.setMinimumSize(1020, 520)
        self.scroll.setWidget(self.scrollWidget)

        self.labels = []
        for i in range(self.img_num):
            label = ClickedQLabel('image', self.scrollWidget)
            label.connect_customized_slot(partial(self.labels_event, i))
            geometry = self.get_geometry(i, self.img_show_size[0], self.img_show_size[1])
            label.move(*geometry)
            label.setFixedSize(self.img_show_size[0], self.img_show_size[1])
            self.labels.append(label)

        # Add tabs to widget
        self.layout.addWidget(self.tab)
        self.layout.addWidget(self.scroll)
        self.setLayout(self.layout)

        # time_stamp = int(time.time())
        # 创建摄像头采集器
        self.cams = []
        for i in range(self.img_num):
            self.cams.append(self._get_cam(i * 2))
        # print(int(time.time())-time_stamp)
        self.img_groups = []
        self.camera_sampling()

    # 图像帧采集，采集到的帧将会存储在list中，并会覆盖旧帧
    def camera_sampling(self):
        self.select_flag = [False] * self.img_num
        self.camera_groups.clear()
        self.img_groups.clear()
        self.camera_name = self.order_input.text().split(',')
        self.camera_id = 0
        self.other_camera_id = 0
        for i in range(self.img_num):
            _, frame = self.cams[i].read()
            # cv2.putText(frame, str(i), (120, 160), cv2.FONT_HERSHEY_COMPLEX, 4.0, (100, 200, 200), 5)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            self.img_groups.append(frame)
            frame = QImage(frame.data, frame.shape[1], frame.shape[0], QImage.Format_RGB888)
            frame_display = QPixmap.fromImage(frame)
            self.labels[i].setPixmap(frame_display)

    def finish(self):
        # print('select finish')
        qApp = QApplication.instance()
        qApp.quit()

    # 点击图像选择摄像头触发的事件，会在图像中显示名称并添加掩膜
    def labels_event(self, i=0):
        if self.select_flag[i]:
            self.camera_sampling()
        else:
            self.select_flag[i] = True
            frame = self.img_groups[i]
            if self.camera_id < len(self.camera_name) and self.camera_name[self.camera_id] != '':
                camera_text = self.camera_name[self.camera_id]
                self.camera_id += 1
            else:
                camera_text = 'other' + str(self.other_camera_id)
                self.other_camera_id += 1
            self.camera_groups[camera_text] = i * 2
            cv2.putText(frame, camera_text, (0, 50), cv2.FONT_HERSHEY_COMPLEX, 2.0, (100, 200, 200), 5)

            zeros = np.zeros((frame.shape), dtype=np.uint8)
            mask = cv2.rectangle(zeros, (0, 0), self.img_show_size, color=(0, 0, 100), thickness=-1)
            frame = cv2.addWeighted(frame, 1, mask, 0.5, 0)

            frame = QImage(frame.data, frame.shape[1], frame.shape[0], QImage.Format_RGB888)
            frame_display = QPixmap.fromImage(frame)
            self.labels[i].setPixmap(frame_display)
            print(self.camera_groups)

    def get_geometry(self, i, w=320, h=240):
        init_x = 10
        init_y = 20
        line_nums = min(self.img_num, 5)
        gap = 20
        x = i % line_nums * (w + gap) + init_x
        y = i // line_nums * (h + gap) + init_y

        return [x, y]

    # 定义摄像头采集器
    def _get_cam(self, index, fps=30):
        cap = cv2.VideoCapture(index)
        time.sleep(0.1)
        cap.release()
        time.sleep(0.1)
        cap = cv2.VideoCapture(index)
        cap.set(6, cv2.VideoWriter.fourcc(*'MJPG'))

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.img_show_size[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.img_show_size[1])
        cap.set(cv2.CAP_PROP_FPS, fps)

        return cap

    # 释放摄像头
    def _release_cam(self, cam):
        cam.release()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    app = QApplication(sys.argv)

    camera_groups = {'leftup': 0}
    ex = PreSetApp(camera_groups, 1)
    ex.show()

    sys.exit(app.exec_())
