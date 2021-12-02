import sys
import time
from functools import partial

import cv2
import matplotlib
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog,
                             QFormLayout, QGridLayout, QGroupBox, QHBoxLayout,
                             QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QPushButton, QScrollArea, QSizePolicy,
                             QVBoxLayout, QWidget)

matplotlib.use('Qt5Agg')
import numpy as np
from matplotlib.backends.backend_qt5agg import \
    FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtCore import pyqtSignal

from .Inference import Inference


class ClickedQLabel(QLabel):
    button_clicked_signal = pyqtSignal()

    def __init__(self, *__args):
        super(ClickedQLabel, self).__init__(*__args)

    def mouseReleaseEvent(self, QMouseEvent):
        self.button_clicked_signal.emit()

    def connect_customized_slot(self, func):
        self.button_clicked_signal.connect(func)


class PresetTableWidget(QWidget):
    def __init__(self, camera_groups, camera_num):
        super(QWidget, self).__init__()
        self.camera_groups = camera_groups
        self.img_num = camera_num
        self.select_flag = []
        self.camera_name = []
        self.camera_id = 0
        self.other_camera_id = 0
        self.img_show_size = (640, 480)
        # Create first tab
        self.layout = QVBoxLayout(self)
        self.tab = QWidget()
        self.setMinimumHeight(150)
        self.Hlayout = QHBoxLayout(self.tab)

        order_text = QLabel('选择顺序：', self)
        self.order_base_text = 'LeftUp,Left,Up,Mid,Down,Right,RightUp'
        self.order_input = QLineEdit(self)
        self.order_input.setText(self.order_base_text)
        self.order_input.setMinimumSize(400, 50)

        button = QPushButton("重新采样", self)
        button.setMinimumSize(150, 50)
        button.clicked.connect(self.camera_sampling)

        self.Hlayout.addStretch(15)
        self.Hlayout.addWidget(order_text)
        self.Hlayout.addWidget(self.order_input)
        self.Hlayout.addStretch(1)
        self.Hlayout.addWidget(button)
        self.Hlayout.addStretch(1)

        self.scrollWidget = QWidget()
        self.scrollWidget.setMinimumSize(4000, 4000)
        self.scroll = QScrollArea(self)
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

        # 创建摄像头采集器
        self.cams = []
        for i in range(self.img_num):
            self.cams.append(self._get_cam(i * 2))
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
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            self.img_groups.append(frame)
            frame = QImage(frame.data, frame.shape[1], frame.shape[0], QImage.Format_RGB888)
            frame_display = QPixmap.fromImage(frame)
            self.labels[i].setPixmap(frame_display)

    def finish(self):
        app = QApplication(sys.argv)
        sys.exit(app.exec_())

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


class RecordTab(QWidget):
    def __init__(self, camera_groups, status_dict, tabs):
        super(QWidget, self).__init__()
        self.camera_groups = camera_groups
        self.camera_num = len(self.camera_groups)
        self.status_dict = status_dict
        self.state = self.status_dict['status']
        self.img_show_size = (640, 480)
        self.resolution = self.status_dict['record_pixel']
        self.fps = self.status_dict['record_fps']
        self.ratio = self.status_dict['record_ratio']
        self.tabs = tabs

        self.layout = QVBoxLayout(self)

        #录制模式
        self.groupBox = QGroupBox("基础操作", self)
        self.groupBox.setMinimumSize(1060, 145)

        self.group_layout = QVBoxLayout(self.groupBox)
        self.group_layout1 = QHBoxLayout()

        self.button_file = QPushButton("选择路径", self.groupBox)
        self.button_file.clicked.connect(self.openFile)
        self.button_file.setMinimumSize(150, 50)
        self.button_file.setMaximumWidth(150)
        self.filePath = QLineEdit(self.groupBox)
        self.input_base_text = '/data/FatigueViewRecoder'
        self.filePath.setText(self.input_base_text)
        self.filePath.setMinimumSize(250, 50)
        self.filePath.setMaximumWidth(2000)

        self.recordCB = []
        note_label = QLabel('分辨率：', self.groupBox)
        self.resolutionCB = QComboBox(self.groupBox)
        self.resolutionCB.addItems(['1080p', '720p', '480p', '360p'])
        self.resolutionCB.currentIndexChanged[int].connect(self.GetResolutionValue)
        self.resolutionCB.setMinimumSize(150, 50)
        self.recordCB.append(self.resolutionCB)
        fromlayout1 = QFormLayout()
        fromlayout1.addRow(note_label, self.resolutionCB)

        note_label = QLabel('帧率：', self.groupBox)
        self.fpsCB = QComboBox(self.groupBox)
        self.fpsCB.addItems(['MaxFps', '30/s', '60/s', '90/s'])
        self.fpsCB.currentIndexChanged[int].connect(self.GetFpsValue)
        self.fpsCB.setMinimumSize(150, 50)
        self.recordCB.append(self.fpsCB)
        fromlayout2 = QFormLayout()
        fromlayout2.addRow(note_label, self.fpsCB)

        note_label = QLabel('压缩率：', self.groupBox)
        self.ratioCB = QComboBox(self.groupBox)
        self.ratioCB.addItems(['100%'])
        self.ratioCB.currentIndexChanged[int].connect(self.GetRatioValue)
        self.ratioCB.setMinimumSize(150, 50)
        self.recordCB.append(self.ratioCB)
        fromlayout3 = QFormLayout()
        fromlayout3.addRow(note_label, self.ratioCB)

        white_label = QLabel('    ', self.groupBox)
        self.group_layout1.addWidget(self.button_file)
        self.group_layout1.addWidget(self.filePath)
        self.group_layout1.addWidget(white_label)
        self.group_layout1.addLayout(fromlayout1)
        self.group_layout1.addWidget(white_label)
        self.group_layout1.addLayout(fromlayout2)
        self.group_layout1.addWidget(white_label)
        self.group_layout1.addLayout(fromlayout3)
        self.group_layout1.addWidget(white_label)
        self.group_layout.addLayout(self.group_layout1)

        self.group_layout2 = QHBoxLayout()

        self.button_record = QPushButton("开始录制", self.groupBox)
        self.button_record.clicked.connect(self.on_click)
        self.button_record.setMinimumSize(150, 50)

        note_label = QLabel(' 备注信息：', self.groupBox)
        note_label.move(175, 105)
        self.note_base_text = "可添加基本备注信息"
        self.note = QLineEdit(self.groupBox)
        self.note.setPlaceholderText(self.note_base_text)
        self.note.setMinimumSize(250, 50)

        state_label = QLabel('状态信息：', self.groupBox)
        self.textBrowser = QLineEdit(self.groupBox)
        self.textBrowser.setStyleSheet("background-color: rgb(151, 205, 177);")
        self.textBrowser.setText(' ')
        self.textBrowser.setMinimumSize(450, 60)

        self.group_layout2.addWidget(self.button_record)
        self.group_layout2.addWidget(note_label)
        self.group_layout2.addWidget(self.note)
        self.group_layout2.addWidget(state_label)
        self.group_layout2.addWidget(self.textBrowser)
        self.group_layout.addLayout(self.group_layout2)

        self.layout.addWidget(self.groupBox)

        #相机画面
        self.note_label = QLabel('录制画面', self)
        self.note_label.setStyleSheet("font-size: 30px")
        self.scrollWidget = QWidget()
        self.scrollWidget.setMinimumSize(1040, 1350)
        self.scroll = QScrollArea(self)
        self.scroll.setWidget(self.scrollWidget)

        scroll_layout = QVBoxLayout(self.scroll)
        grid_layout = QGridLayout()

        self.img_labels = []
        for i, (key, _) in enumerate(self.camera_groups.items()):
            img_layout = QVBoxLayout()
            note_label = QLabel("位置：" + key, self.scrollWidget)
            note_label.setMaximumHeight(30)
            label = QLabel('image', self.scrollWidget)
            label.setMinimumSize(self.img_show_size[0], self.img_show_size[1])
            self.img_labels.append(label)
            img_layout.addWidget(note_label)
            img_layout.addStretch(0)
            img_layout.addWidget(label)
            img_layout.addStretch(1)
            grid_layout.addLayout(img_layout, i // 5, i % 5)

        scroll_layout.addLayout(grid_layout)
        scroll_layout.addStretch(10)

        self.layout.addWidget(self.note_label)
        self.layout.addWidget(self.scroll)
        self.setLayout(self.layout)

    def openFile(self):
        get_directory_path = QFileDialog.getExistingDirectory(self, "选择存储文件夹", "/")
        self.filePath.setText(str(get_directory_path))
        self.status_dict['dir_info'] = self.filePath.text()

    def GetResolutionValue(self, val):
        resolution_map = [(1920, 1080), (1280, 720), (720, 480), (600, 360)]
        self.resolution = resolution_map[val]

    def GetFpsValue(self, val):
        fps_map = [0, 30, 60, 90]
        self.fps = fps_map[val]

    def GetRatioValue(self, val):
        ratio_map = [100, 70, 50, 30]
        self.ratio = ratio_map[val]

    def get_geometry(self, i, w=320, h=240):
        init_x = 10
        init_y = 10
        line_nums = min(self.camera_num, 3)
        gap = 30
        x = i % line_nums * (w + gap) + init_x
        y = i // line_nums * (h + gap) + init_y

        return [x, y]

    def show_cam(self, img, i):
        img = cv2.resize(img, self.img_show_size)
        if len(img.shape) == 3:
            frame = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        else:
            frame = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        img = QImage(frame.data, frame.shape[1], frame.shape[0], QImage.Format_RGB888)
        img_small = QPixmap.fromImage(img)

        self.img_labels[i].setPixmap(img_small)

    def keyPressEvent(self, event):
        if self.client_server == 'server':
            key = event.key()

            if key == Qt.Key_Space:
                self.on_click()
            elif key == Qt.Key_Q:
                self.status_dict['status'] = -100

    def on_click(self):

        if self.state == 0:
            self.state = 1
            self.button_record.setText('结束录制')

            if self.status_dict is not None:
                self.status_dict['dir_info'] = self.filePath.text()
                self.status_dict['note'] = self.note.text()
                self.status_dict['record_pixel'] = self.resolution
                self.status_dict['record_fps'] = self.fps
                self.status_dict['record_ratio'] = self.ratio
                self.status_dict['status'] = 2

            for cb in self.recordCB:
                cb.setEnabled(False)
            self.tabs.setTabEnabled(1, False)
        else:
            self.state = 0
            self.button_record.setText('开始录制')

            for cb in self.recordCB:
                cb.setEnabled(True)
            self.tabs.setTabEnabled(1, True)

            if self.status_dict is not None:
                self.status_dict['status'] = 0
            time.sleep(0.5)

    def system_restart(self):
        self.status_dict['is_restart'] = True
        qApp = QApplication.instance()
        qApp.quit()


class TestTab(QWidget):
    def __init__(self, camera_groups, status_dict, infer_mask, tabs):
        super(QWidget, self).__init__()

        self.camera_groups = camera_groups
        self.status_dict = status_dict
        self.infer_mask = infer_mask
        self.state = self.status_dict['status']
        self.tabs = tabs
        print('testtab', self.camera_groups)
        self.img_num = len(self.camera_groups)
        self.img_show_size = (480, 360)

        self.buttons = []
        self.textBrowsers = []

        self.layout = QVBoxLayout(self)

        #基础操作
        self.groupBox = QGroupBox("基础操作", self)

        self.button_test = QPushButton("开始测试", self.groupBox)
        self.button_test.clicked.connect(self.switch_is_infer)
        self.button_test.setMinimumSize(150, 50)

        self.button_record = QPushButton("开始录制", self.groupBox)
        self.button_record.clicked.connect(self.on_click)
        self.button_record.setMinimumSize(150, 50)

        self.button_file = QPushButton("选择路径", self.groupBox)
        self.button_file.clicked.connect(self.openFile)
        self.button_file.setMinimumSize(150, 50)
        self.filePath = QLineEdit(self.groupBox)
        self.input_base_text = '/data/FatigueViewRecoder'
        self.filePath.setText(self.input_base_text)
        self.filePath.setMinimumSize(200, 50)
        fromlayout1 = QFormLayout()
        fromlayout1.addRow(self.button_file, self.filePath)

        state_label = QLabel('        状态信息:    ', self.groupBox)
        self.textBrowser = QLineEdit(self.groupBox)
        self.textBrowser.setText(' ')
        self.textBrowser.setStyleSheet("background-color: rgb(151, 205, 177);")
        self.textBrowser.setMinimumSize(500, 60)
        fromlayout2 = QFormLayout()
        fromlayout2.addRow(state_label, self.textBrowser)

        white_label = QLabel('    ', self.groupBox)
        self.layout1 = QVBoxLayout(self.groupBox)
        self.layout2 = QHBoxLayout()
        self.layout2.addWidget(self.button_record)
        self.layout2.addWidget(white_label)
        self.layout2.addLayout(fromlayout1)
        self.layout3 = QHBoxLayout()
        self.layout3.addWidget(self.button_test)
        self.layout3.addLayout(fromlayout2)
        self.layout1.addLayout(self.layout2)
        self.layout1.addLayout(self.layout3)

        self.layout.addWidget(self.groupBox)

        #相机画面
        self.note_label = QLabel('模型测试', self)
        self.note_label.setStyleSheet("font-size: 26px")
        self.scrollWidget = QWidget()
        self.scrollWidget.setMinimumSize(4040, 8650)
        self.scroll = QScrollArea(self)
        self.scroll.setMinimumSize(1020, 520)
        self.scroll.setWidget(self.scrollWidget)

        scroll_layout = QVBoxLayout(self.scroll)
        grid_layout = QGridLayout()

        self.img_labels = []
        self.curve_canvas = []
        self.cc_boxes = []
        self.curve_data = []

        for i, (key, _) in enumerate(self.camera_groups.items()):
            img_layout = QVBoxLayout()
            label_layout = QHBoxLayout()
            loca_label = QLabel("位置：" + key, self.scrollWidget)

            mode_label = QLabel("   模式：", self.scrollWidget)
            CCheckBox = ComboCheckBox(self.scrollWidget)
            CCheckBox.setMinimumSize(150, 50)
            CCheckBox.qLineEdit.setText('w/o test')
            CCheckBox.editTextChanged.connect(partial(self.select_infer_mode, i))
            Flayout0 = QFormLayout()
            Flayout0.addRow(mode_label, CCheckBox)

            label_layout.addWidget(loca_label)
            label_layout.addLayout(Flayout0)
            label_layout.addStretch(1)

            img_layout.addLayout(label_layout)
            img_layout.addStretch(0)

            label_widget = QWidget()
            label_widget.setMinimumSize(self.img_show_size[0], self.img_show_size[1])
            label = QLabel(label_widget)
            label.setFixedSize(self.img_show_size[0], self.img_show_size[1])
            self.img_labels.append(label)
            img_layout.addWidget(label_widget)
            img_layout.addStretch(0)

            num_label = QLabel("数值：", self.scrollWidget)
            CCheckBox = ComboCheckBox(self.scrollWidget, ['w/o show'])
            CCheckBox.setMinimumSize(150, 50)
            CCheckBox.qLineEdit.setText('w/o show')
            self.cc_boxes.append(CCheckBox)

            Flayout1 = QFormLayout()
            Flayout1.addRow(num_label, CCheckBox)
            label_layout = QHBoxLayout()
            label_layout.addLayout(Flayout1)
            label_layout.addStretch(1)

            img_layout.addLayout(label_layout)
            img_layout.addStretch(0)

            graph_label = QWidget(self.scrollWidget)
            graph_label.setFixedSize(self.img_show_size[0] + 20, self.img_show_size[1] + 20)

            vbox = QVBoxLayout(graph_label)
            canvas = CurveCanvas(graph_label, width=3, height=3, dpi=100)
            vbox.addWidget(canvas)
            graph_label.setLayout(vbox)
            self.curve_canvas.append(canvas)

            img_layout.addWidget(graph_label)
            img_layout.addStretch(1)
            grid_layout.addLayout(img_layout, i // 6, i % 6)

        scroll_layout.addLayout(grid_layout)
        scroll_layout.addStretch(10)

        self.layout.addWidget(self.note_label)
        self.layout.addWidget(self.scroll)
        self.setLayout(self.layout)

    def select_infer_mode(self, i, text):
        if text == '':
            return

        self.cc_boxes[i].clear_options()

        if 'w/o test' in text:
            for key, _ in self.infer_mask[i].items():
                self.infer_mask[i][key] = False
            return
        for key, _ in self.infer_mask[i].items():
            if text.find(key) > -1:
                self.infer_mask[i][key] = True
                if key != 'w/o show':
                    self.cc_boxes[i].items.extend(Inference.infer_curve[key])
                # print(key, self.infer_mask[i][key])
            else:
                self.infer_mask[i][key] = False
        self.cc_boxes[i].row_num = len(self.cc_boxes[i].items)
        for j in range(1, self.cc_boxes[i].row_num):
            self.cc_boxes[i].addQCheckBox(j)
        # print(i, 'test_viewer:', self.infer_mask[i])

    def is_inference(self):
        for i, check in enumerate(self.camera_check):
            if check.isChecked():
                self.infer_mask[i] = True
            else:
                self.infer_mask[i] = False

    def show_cam(self, infer, i):
        img, curve_data = infer
        img = cv2.resize(img, self.img_show_size)
        if len(img.shape) == 3:
            frame = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        else:
            frame = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        img = QImage(frame.data, frame.shape[1], frame.shape[0], QImage.Format_RGB888)
        img_small = QPixmap.fromImage(img)

        # if not self.infer_mask[i]['w/o show']:
        self.img_labels[i].setPixmap(img_small)

        show_curve_data = dict()
        for key, val in curve_data.items():
            if key in self.cc_boxes[i].qLineEdit.text():
                show_curve_data[key] = val
        if show_curve_data:
            self.show_curve(show_curve_data, i)

    def show_curve(self, show_curve, i):
        del_data_key = []
        for key, val in self.curve_canvas[i].data.items():
            if key in show_curve:
                data_len = len(self.curve_canvas[i].data[key][0])
                if data_len < 50:
                    self.curve_canvas[i].data[key][0].append(data_len)
                    self.curve_canvas[i].data[key][1].append(show_curve[key])
                else:
                    self.curve_canvas[i].data[key][1][:-1] = self.curve_canvas[i].data[key][1][1:]
                    self.curve_canvas[i].data[key][1][-1] = show_curve[key]
                del show_curve[key]
            else:
                del_data_key.append(key)

        for key in del_data_key:
            del self.curve_canvas[i].data[key]

        for key, val in show_curve.items():
            self.curve_canvas[i].data[key] = [[0], [val]]

        self.curve_canvas[i].display_curve()

    def openFile(self):
        get_directory_path = QFileDialog.getExistingDirectory(self, "选择存储文件夹", "/")
        self.filePath.setText(str(get_directory_path))
        self.status_dict['dir_info'] = self.filePath.text()

    def on_click(self):

        if self.state == 0:
            self.state = 1
            self.button_record.setText('结束录制')
            # self.button_record.setStyleSheet("background-color: red")

            if self.status_dict is not None:
                self.status_dict['dir_info'] = self.filePath.text()
                self.status_dict['status'] = 2

            self.tabs.setTabEnabled(0, False)

        else:
            self.state = 0
            self.button_record.setText('开始录制')
            # self.button_record.setStyleSheet("background-color: green")

            if self.status_dict is not None:
                self.status_dict['status'] = 0

            self.tabs.setTabEnabled(0, True)
            time.sleep(0.5)

    def get_geometry(self, i, w=320, h=240):
        init_x = 10
        init_y = 30
        h += h + 30
        line_nums = min(self.img_num, 3)
        gap = 30
        x = i % line_nums * (w + gap) + init_x
        y = i // line_nums * (h + gap) + init_y

        return [x, y]

    def select_camera(self):
        qApp = QApplication.instance()
        qApp.quit()

    def switch_is_infer(self):
        if not self.status_dict['is_infer']:
            self.button_test.setText('测试中')
            # self.button_test.setStyleSheet("background-color: red")
        else:
            self.button_test.setText('开始测试')
            # self.button_test.setStyleSheet("background-color: green")

        self.status_dict['is_infer'] = not self.status_dict['is_infer']
        time.sleep(0.5)

    def reset_camera(self):
        if self.status_dict['reset_flag'] == 0:
            self.status_dict['reset_flag'] = 1
            self.button_reset.setText('开始重置')
            # self.button_reset.setStyleSheet("background-color: red")
        else:
            self.status_dict['reset_flag'] = 0
            self.button_reset.setText('重置摄像头')
            # self.button_reset.setStyleSheet("background-color: green")
            for i, map_label in enumerate(self.camera_maps):
                self.img_map[i] = map_label.text()

        time.sleep(0.5)


class CurveCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):

        self.data = dict()

        self.fig = Figure(facecolor='#EFEFEF', figsize=(width, height), dpi=dpi)

        self.ax = self.fig.add_axes([0.1, 0.1, 0.87, 0.87])

        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    def display_curve(self):
        self.ax.clear()
        for key, val in self.data.items():
            self.ax.plot(val[0], val[1], label=key)
        self.ax.legend(loc=2)
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()


class ComboCheckBox(QComboBox):
    def __init__(self, parent, items=None):
        super(ComboCheckBox, self).__init__(parent)
        if items is not None:
            self.items = items
        else:
            self.items = ['w/o show', 'fatigue', 'smoke', 'emotion']
        self.row_num = len(self.items)
        self.Selectedrow_num = 0
        self.qCheckBox = []
        self.qLineEdit = QLineEdit()
        self.qLineEdit.setReadOnly(True)
        self.qListWidget = QListWidget()
        self.setModel(self.qListWidget.model())
        self.setView(self.qListWidget)
        self.setLineEdit(self.qLineEdit)
        for i in range(self.row_num):
            self.addQCheckBox(i)

    def addQCheckBox(self, i):
        self.qCheckBox.append(QCheckBox())
        qItem = QListWidgetItem(self.qListWidget)
        self.qCheckBox[i].setText(self.items[i])
        self.qListWidget.setItemWidget(qItem, self.qCheckBox[i])

        self.qCheckBox[i].stateChanged.connect(self.show)

    def Selectlist(self):
        Outputlist = []
        if self.qCheckBox[0].isChecked() == True:
            for i in range(1, self.row_num):
                self.qCheckBox[i].setChecked(False)
                self.qCheckBox[i].setEnabled(False)
            Outputlist.append(self.qCheckBox[0].text())
            return Outputlist
        else:
            for i in range(1, self.row_num):
                self.qCheckBox[i].setEnabled(True)
        for i in range(1, self.row_num):
            if self.qCheckBox[i].isChecked() == True:
                Outputlist.append(self.qCheckBox[i].text())
        self.Selectedrow_num = len(Outputlist)
        return Outputlist

    def show(self):
        for i in range(self.row_num):
            self.qCheckBox[i].stateChanged.disconnect()

        show = ''
        Outputlist = self.Selectlist()
        self.qLineEdit.setReadOnly(False)
        self.qLineEdit.clear()
        for mode in Outputlist:
            show += mode + ';'
        if show == '':
            show = 'w/o test'
        self.qLineEdit.setText(show)
        self.qLineEdit.setReadOnly(True)

        for i in range(self.row_num):
            self.qCheckBox[i].stateChanged.connect(self.show)

    def clear_check(self):
        for i in range(self.row_num):
            self.qCheckBox[i].setChecked(False)

    def clear_options(self):
        self.qListWidget.clear()
        self.qCheckBox.clear()
        self.items = ['w/o show']
        self.addQCheckBox(0)
        self.row_num = 1
        self.qLineEdit.setText(self.items[0])


'''first'''


class J3_DVB(QWidget):
    def __init__(self):
        super(QWidget, self).__init__()

        self.groupBox = QGroupBox("J3 DVB Record", self)
        self.groupBox.setMinimumSize(1400, 145)

        self.group_layout = QVBoxLayout(self.groupBox)
        self.group_layout1 = QHBoxLayout()

        self.button_file = QPushButton("选择路径", self.groupBox)
        self.button_file.clicked.connect(self.openFile)
        self.button_file.setMinimumSize(150, 50)
        self.button_file.setMaximumWidth(150)
        self.filePath = QLineEdit(self.groupBox)
        self.input_base_text = '/data/FatigueViewRecoder'
        self.filePath.setText(self.input_base_text)
        self.filePath.setMinimumSize(500, 50)
        self.filePath.setMaximumWidth(2000)

        self.recordCB = []
        note_label = QLabel('分辨率：', self.groupBox)
        self.resolutionCB = QComboBox(self.groupBox)
        self.resolutionCB.addItems(['1080p', '720p', '480p', '360p'])
        self.resolutionCB.currentIndexChanged[int].connect(self.GetResolutionValue)
        self.resolutionCB.setMinimumSize(150, 50)
        self.recordCB.append(self.resolutionCB)
        fromlayout1 = QFormLayout()
        fromlayout1.addRow(note_label, self.resolutionCB)

        note_label = QLabel('帧率：', self.groupBox)
        self.fpsCB = QComboBox(self.groupBox)
        self.fpsCB.addItems(['MaxFps', '30/s', '60/s', '90/s'])
        self.fpsCB.currentIndexChanged[int].connect(self.GetFpsValue)
        self.fpsCB.setMinimumSize(150, 50)
        self.recordCB.append(self.fpsCB)
        fromlayout2 = QFormLayout()
        fromlayout2.addRow(note_label, self.fpsCB)

        note_label = QLabel('压缩率：', self.groupBox)
        self.ratioCB = QComboBox(self.groupBox)
        self.ratioCB.addItems(['100%'])
        self.ratioCB.currentIndexChanged[int].connect(self.GetRatioValue)
        self.ratioCB.setMinimumSize(150, 50)
        self.recordCB.append(self.ratioCB)
        fromlayout3 = QFormLayout()
        fromlayout3.addRow(note_label, self.ratioCB)

        white_label = QLabel('    ', self.groupBox)
        self.group_layout1.addWidget(self.button_file)
        self.group_layout1.addWidget(self.filePath)
        self.group_layout1.addWidget(white_label)
        self.group_layout1.addLayout(fromlayout1)
        self.group_layout1.addWidget(white_label)
        self.group_layout1.addLayout(fromlayout2)
        self.group_layout1.addWidget(white_label)
        self.group_layout1.addLayout(fromlayout3)
        self.group_layout1.addWidget(white_label)
        self.group_layout.addLayout(self.group_layout1)

        self.group_layout2 = QHBoxLayout()

        self.button_record = QPushButton("开始录制", self.groupBox)
        self.button_record.clicked.connect(self.on_click)
        self.button_record.setMinimumSize(150, 50)

        note_label = QLabel(' 备注信息：', self.groupBox)
        note_label.move(175, 105)
        self.note_base_text = "可添加基本备注信息"
        self.note = QLineEdit(self.groupBox)
        self.note.setPlaceholderText(self.note_base_text)
        self.note.setMinimumSize(250, 50)

        self.group_layout2.addWidget(self.button_record)
        self.group_layout2.addWidget(note_label)
        self.group_layout2.addWidget(self.note)
        self.group_layout.addLayout(self.group_layout2)

    def openFile(self):
        get_directory_path = QFileDialog.getExistingDirectory(self, "选择存储文件夹", "/")
        self.filePath.setText(str(get_directory_path))
        self.status_dict['dir_info'] = self.filePath.text()

    def GetResolutionValue(self, val):
        resolution_map = [(1920, 1080), (1280, 720), (720, 480), (600, 360)]
        self.resolution = resolution_map[val]

    def GetFpsValue(self, val):
        fps_map = [0, 30, 60, 90]
        self.fps = fps_map[val]

    def GetRatioValue(self, val):
        ratio_map = [100, 70, 50, 30]
        self.ratio = ratio_map[val]

    def get_geometry(self, i, w=320, h=240):
        init_x = 10
        init_y = 10
        line_nums = min(self.camera_num, 3)
        gap = 30
        x = i % line_nums * (w + gap) + init_x
        y = i // line_nums * (h + gap) + init_y

        return [x, y]

    def show_cam(self, img, i):
        img = cv2.resize(img, self.img_show_size)
        if len(img.shape) == 3:
            frame = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        else:
            frame = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        img = QImage(frame.data, frame.shape[1], frame.shape[0], QImage.Format_RGB888)
        img_small = QPixmap.fromImage(img)

        self.img_labels[i].setPixmap(img_small)

    def keyPressEvent(self, event):
        if self.client_server == 'server':
            key = event.key()

            if key == Qt.Key_Space:
                self.on_click()
            elif key == Qt.Key_Q:
                self.status_dict['status'] = -100

    def on_click(self):

        if self.state == 0:
            self.state = 1
            self.button_record.setText('结束录制')

            if self.status_dict is not None:
                self.status_dict['dir_info'] = self.filePath.text()
                self.status_dict['note'] = self.note.text()
                self.status_dict['record_pixel'] = self.resolution
                self.status_dict['record_fps'] = self.fps
                self.status_dict['record_ratio'] = self.ratio
                self.status_dict['status'] = 2

            for cb in self.recordCB:
                cb.setEnabled(False)
            self.tabs.setTabEnabled(1, False)
        else:
            self.state = 0
            self.button_record.setText('开始录制')

            for cb in self.recordCB:
                cb.setEnabled(True)
            self.tabs.setTabEnabled(1, True)

            if self.status_dict is not None:
                self.status_dict['status'] = 0
            time.sleep(0.5)

    def system_restart(self):
        self.status_dict['is_restart'] = True
        qApp = QApplication.instance()
        qApp.quit()


''' second '''


class Upload(QWidget):
    def __init__(self):
        super(QWidget, self).__init__()
        self.groupBox = QGroupBox("上传视频", self)
        self.groupBox.setMinimumSize(1400, 145)

        self.group_layout = QVBoxLayout(self.groupBox)
        self.group_layout1 = QHBoxLayout()

        self.button_file = QPushButton("选择路径", self.groupBox)
        self.button_file.clicked.connect(self.openFile)
        self.button_file.setMinimumSize(150, 50)
        self.button_file.setMaximumWidth(150)
        self.filePath = QLineEdit(self.groupBox)
        self.input_base_text = '/data/FatigueViewRecoder'
        self.filePath.setText(self.input_base_text)
        self.filePath.setMinimumSize(500, 50)
        self.filePath.setMaximumWidth(2000)

        self.button_record = QPushButton("开始上传", self.groupBox)
        self.button_record.clicked.connect(self.on_click)
        self.button_record.setMinimumSize(150, 50)

        note_label = QLabel(' 备注信息：', self.groupBox)
        note_label.move(175, 105)
        self.note_base_text = "可添加基本备注信息"
        self.note = QLineEdit(self.groupBox)
        self.note.setPlaceholderText(self.note_base_text)
        self.note.setMinimumSize(250, 50)

        self.group_layout1.addWidget(self.button_file)
        self.group_layout1.addWidget(self.filePath)
        self.group_layout.addLayout(self.group_layout1)

        self.group_layout2 = QHBoxLayout()
        self.group_layout2.addWidget(self.button_record)
        self.group_layout2.addWidget(note_label)
        self.group_layout2.addWidget(self.note)
        self.group_layout.addLayout(self.group_layout2)

    def openFile(self):
        get_directory_path = QFileDialog.getExistingDirectory(self, "选择存储文件夹", "/")
        self.filePath.setText(str(get_directory_path))
        self.status_dict['dir_info'] = self.filePath.text()

    def GetResolutionValue(self, val):
        resolution_map = [(1920, 1080), (1280, 720), (720, 480), (600, 360)]
        self.resolution = resolution_map[val]

    def GetFpsValue(self, val):
        fps_map = [0, 30, 60, 90]
        self.fps = fps_map[val]

    def GetRatioValue(self, val):
        ratio_map = [100, 70, 50, 30]
        self.ratio = ratio_map[val]

    def get_geometry(self, i, w=320, h=240):
        init_x = 10
        init_y = 10
        line_nums = min(self.camera_num, 3)
        gap = 30
        x = i % line_nums * (w + gap) + init_x
        y = i // line_nums * (h + gap) + init_y

        return [x, y]

    def show_cam(self, img, i):
        img = cv2.resize(img, self.img_show_size)
        if len(img.shape) == 3:
            frame = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        else:
            frame = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        img = QImage(frame.data, frame.shape[1], frame.shape[0], QImage.Format_RGB888)
        img_small = QPixmap.fromImage(img)

        self.img_labels[i].setPixmap(img_small)

    def keyPressEvent(self, event):
        if self.client_server == 'server':
            key = event.key()

            if key == Qt.Key_Space:
                self.on_click()
            elif key == Qt.Key_Q:
                self.status_dict['status'] = -100

    def on_click(self):

        if self.state == 0:
            self.state = 1
            self.button_record.setText('结束录制')

            if self.status_dict is not None:
                self.status_dict['dir_info'] = self.filePath.text()
                self.status_dict['note'] = self.note.text()
                self.status_dict['record_pixel'] = self.resolution
                self.status_dict['record_fps'] = self.fps
                self.status_dict['record_ratio'] = self.ratio
                self.status_dict['status'] = 2

            for cb in self.recordCB:
                cb.setEnabled(False)
            self.tabs.setTabEnabled(1, False)
        else:
            self.state = 0
            self.button_record.setText('开始录制')

            for cb in self.recordCB:
                cb.setEnabled(True)
            self.tabs.setTabEnabled(1, True)

            if self.status_dict is not None:
                self.status_dict['status'] = 0
            time.sleep(0.5)

    def system_restart(self):
        self.status_dict['is_restart'] = True
        qApp = QApplication.instance()
        qApp.quit()


''' third '''


class Help(QWidget):
    def __init__(self):
        super(QWidget, self).__init__()
        self.groupBox = QGroupBox("帮助", self)
        self.groupBox.setMinimumSize(1400, 145)

        self.group_layout = QVBoxLayout(self.groupBox)
        self.group_layout1 = QHBoxLayout()

        note_label = QLabel(' 帮助信息：', self.groupBox)
        note_label.move(175, 105)
        self.note_base_text = "这是多路摄像机"
        self.note = QLineEdit(self.groupBox)
        self.note.setPlaceholderText(self.note_base_text)
        self.note.setMinimumSize(250, 50)

        self.group_layout2 = QHBoxLayout()
        self.group_layout2.addWidget(note_label)
        self.group_layout2.addWidget(self.note)
        self.group_layout.addLayout(self.group_layout2)
