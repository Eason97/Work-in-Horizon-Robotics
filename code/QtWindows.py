import sys
import threading
from multiprocessing import Lock

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (QApplication, QComboBox, QDesktopWidget,
                             QMainWindow, QMessageBox, QTabWidget, QVBoxLayout,
                             QWidget)

from .TabsViewer import (J3_DVB, Help, PresetTableWidget, RecordTab, TestTab,
                         Upload)


# 主控制界面，包含录制与测试界面
class App(QMainWindow):
    def __init__(self, button_num, img_pipes, status_dict, img_map, infer_mask, camera_groups, no_show_flag,
                 client_server):
        super().__init__()
        self.client_server = client_server
        self.title = 'Beelab'

        self.status_dict = status_dict
        self.viewer_out_pipes = img_pipes[-2]

        self.left = 0
        self.top = 0
        self.width = 1100
        self.height = 800

        self.setWindowTitle(self.title)
        self.table_widget = MyTableWidget(self, button_num, img_pipes, status_dict, img_map, infer_mask, camera_groups,
                                          no_show_flag, client_server)
        # 加载QSS界面美化文件
        with open("style/style.qss", encoding='utf-8') as f:
            qss = f.read()
        self.table_widget.setStyleSheet(qss)
        self.setCentralWidget(self.table_widget)
        self.show()
        self.setWindowState(Qt.WindowMaximized)

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    # 窗口关闭事件
    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Beelab', "是否要退出程序？", QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            self.status_dict['status'] = -100
            for out_pipe in self.viewer_out_pipes:
                out_pipe.put(False)
            event.accept()
        else:
            event.ignore()


class MyTableWidget(QWidget):
    def __init__(self, parent, button_num, img_pipes, status_dict, img_map, infer_mask, camera_groups, no_show_flag,
                 client_server):
        super(QWidget, self).__init__(parent)
        self.layout = QVBoxLayout(self)

        self.client_server = client_server
        self.state = 0
        self.status_dict = status_dict
        self.work_mode = self.status_dict['work_mode']  # 工作模式标识；0：录制模式，1：测试模式
        self.img_pipes = img_pipes
        self.img_num = len(img_pipes[0])
        self.img_map = img_map
        self.infer_mask = infer_mask
        self.camera_groups = camera_groups
        self.no_show_flag = no_show_flag

        self.img_show_size = (320, 240)

        self.show_img_id = 0

        # Initialize tab screen
        self.tabs = QTabWidget()
        if button_num == 0:
            self.tab0 = PresetTableWidget(self.camera_groups, 1)
            self.tabs.addTab(self.tab0, "camera")
            self.tabs.resize(1000, 800)

        if button_num == 1:  # record
            self.tab1 = RecordTab(self.camera_groups, self.status_dict, self.tabs)
            self.tab2 = TestTab(self.camera_groups, self.status_dict, self.infer_mask, self.tabs)
            self.tab3 = J3_DVB()
            self.tab4 = Upload()
            self.tab5 = Help()
            self.tabs.resize(1000, 800)

            self.tabs.addTab(self.tab1, "录制模式")
            self.tabs.addTab(self.tab2, "测试模式")
            self.tabs.addTab(self.tab3, "J3 DVB Record")
            self.tabs.addTab(self.tab4, "上传")
            self.tabs.addTab(self.tab5, "帮助")
            self.tabs.currentChanged.connect(self.switch_work_mode)

        if button_num == 2:  #test
            self.tab1 = RecordTab(self.camera_groups, self.status_dict, self.tabs)
            self.tab2 = TestTab(self.camera_groups, self.status_dict, self.infer_mask, self.tabs)
            self.tab3 = J3_DVB()
            self.tab4 = Upload()
            self.tab5 = Help()
            self.tabs.resize(1000, 800)

            self.tabs.addTab(self.tab2, "测试模式")
            self.tabs.addTab(self.tab1, "录制模式")
            self.tabs.addTab(self.tab3, "J3 DVB Record")
            self.tabs.addTab(self.tab4, "上传")
            self.tabs.addTab(self.tab5, "帮助")
            self.status_dict['work_mode_temp'] = 1
            self.tabs.currentChanged.connect(self.switch_work_mode)

        if button_num == 3:
            self.tab1 = J3_DVB()
            self.tab2 = RecordTab(self.camera_groups, self.status_dict, self.tabs)
            self.tab3 = TestTab(self.camera_groups, self.status_dict, self.infer_mask, self.tabs)
            self.tab4 = Upload()
            self.tab5 = Help()
            self.tabs.resize(1000, 800)

            self.tabs.addTab(self.tab1, "J3 DVB Record")
            self.tabs.addTab(self.tab2, "录制模式")
            self.tabs.addTab(self.tab3, "测试模式")
            self.tabs.addTab(self.tab4, "上传")
            self.tabs.addTab(self.tab5, "帮助")
            self.tabs.currentChanged.connect(self.switch_work_mode)
        if button_num == 4:
            self.tab1 = Upload()
            self.tab2 = RecordTab(self.camera_groups, self.status_dict, self.tabs)
            self.tab3 = TestTab(self.camera_groups, self.status_dict, self.infer_mask, self.tabs)
            self.tab4 = J3_DVB()
            self.tab5 = Help()
            self.tabs.resize(1000, 800)

            self.tabs.addTab(self.tab1, "上传")
            self.tabs.addTab(self.tab2, "录制模式")
            self.tabs.addTab(self.tab3, "测试模式")
            self.tabs.addTab(self.tab4, "J3 DVB Record")
            self.tabs.addTab(self.tab5, "帮助")
            self.tabs.currentChanged.connect(self.switch_work_mode)

        if button_num == 5:
            self.tab1 = Help()
            self.tab2 = RecordTab(self.camera_groups, self.status_dict, self.tabs)
            self.tab3 = TestTab(self.camera_groups, self.status_dict, self.infer_mask, self.tabs)
            self.tab4 = J3_DVB()
            self.tab5 = Upload()
            self.tabs.resize(1000, 800)

            self.tabs.addTab(self.tab1, "帮助")
            self.tabs.addTab(self.tab2, "录制模式")
            self.tabs.addTab(self.tab3, "测试模式")
            self.tabs.addTab(self.tab4, "J3 DVB Record")
            self.tabs.addTab(self.tab5, "上传")
            self.tabs.currentChanged.connect(self.switch_work_mode)

        # Add tabs to widget
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

        self.show_lock = Lock()

        self.th = threading.Thread(target=self.show_cam)
        self.th.start()

        self.timer = QTimer()
        self.timer.timeout.connect(self.show_text)
        self.timer.start(500)

    def get_QComboBox(self, tab):
        cb = QComboBox(tab)
        items = ['选择画面']
        for i in range(self.img_num):
            if i < self.img_num / 2:
                items.append('IR:{}'.format(i))
            else:
                items.append('RGB:{}'.format(i - self.img_num / 2))
        cb.addItems(items)
        return cb

    # 切换tab触发的事件
    def switch_work_mode(self):
        self.status_dict['work_mode_temp'] = self.tabs.currentIndex()

    # 相机画面实时展示
    def show_cam(self):
        img_pipes, inference_pipes, viewer_out_pipes, viewer_begin = self.img_pipes
        while self.status_dict['status'] != -100:
            # count += 1
            viewer_begin.get(True)
            for i, (img_pipe, inference_pipe,
                    viewer_out_pip) in enumerate(zip(img_pipes, inference_pipes, viewer_out_pipes)):
                if self.status_dict['work_mode'] == 1 and self.no_show_flag[i]:
                    continue

                img_info, img = img_pipe.get(True)

                if self.status_dict['work_mode'] == 0:
                    self.tab1.show_cam(img, i)
                else:
                    infer_info, infer = inference_pipe.get(True)
                    self.tab2.show_cam(infer, i)

                # viewer_out_pip.put(img_info)

            # cv2.waitKey(1)

    # 帧率等状态信息显示
    def show_text(self):
        frame_index = self.status_dict['frame_id']
        speed = self.status_dict['fps']
        now_time = self.status_dict['time']
        if self.status_dict['status'] != 1:
            now_time = 0
        info = '已录制 {}s; 当前帧：{} ; 帧率：{}/s'.format(now_time, frame_index, speed)
        # for textBrowser in self.tab2.textBrowsers:
        if self.status_dict['work_mode'] == 0:
            self.tab1.textBrowser.setText(info)
        else:
            self.tab2.textBrowser.setText(info)

    def selectionchange(self, i):
        if i > 0:
            self.show_img_id = i - 1


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App(None, None, None, None, 'server')
    sys.exit(app.exec_())
