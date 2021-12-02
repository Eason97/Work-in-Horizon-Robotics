import sys
from multiprocessing import Process

from PyQt5.QtWidgets import QApplication

from .Preset_QtWin import PreSetApp


class PresetViewer(Process):
    def __init__(self, camera_groups, camera_num):
        Process.__init__(self)
        self.camera_groups = camera_groups
        self.camera_num = camera_num

    def run(self):
        app = QApplication([])
        PreSetExe = PreSetApp(self.camera_groups, self.camera_num)
        sys.exit(app.exec_())
