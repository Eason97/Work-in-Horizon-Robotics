import time
from multiprocessing import Process

import cv2
import numpy as np


class Camera(Process):
    def __init__(self):
        Process.__init__(self)

        self.in_pipe = None
        self.out_pipe = None
        self.signal_pipe = None
        self.viewew_out_pipe = None
        self.status_dict = None

    def set_pipe(self, in_pipe=None, out_pipe=None, signal_pip=None, viewew_out_pipe=None):
        self.in_pipe = in_pipe
        self.out_pipe = out_pipe
        self.signal_pipe = signal_pip
        self.viewew_out_pipe = viewew_out_pipe

    def set_status_dict(self, status_dict=None):
        self.status_dict = status_dict

    def _get_cam(self):
        pass

    def _get_frame(self, cam):
        pass

    def _release_cam(self, cam):
        pass

    def run(self):
        cam = self._get_cam()

        if self.in_pipe is None and self.out_pipe is None:
            return 0
        # count = -1
        while True:
            in_info = 0
            if self.in_pipe is not None:
                in_info = self.in_pipe.get(True)

                if in_info is False:
                    self._release_cam(cam)
                    break

            img = self._get_frame(cam)

            tic = int(time.time() * 1000)
            in_info = [in_info, tic]

            if self.out_pipe is not None:
                if isinstance(self.out_pipe, list):
                    for i, pip in enumerate(self.out_pipe):
                        # if i == 1:
                        #     count += 1
                        #     if count % 5 != 0:
                        #         continue
                        if self.status_dict['work_mode'] == 0 and i == 0:  # 录制模式下不向预测进程发送图像帧
                            continue
                        if self.status_dict['work_mode'] == 1 and i == 2:  # 测试模式下不向存储进程发送图像帧
                            continue
                        if i == 1 and pip.qsize() > 0:
                            continue
                        if i == 0 and pip.qsize() > 0:
                            continue
                        pip.put([in_info, img])
                else:
                    self.out_pipe.put([in_info, img])

            # if self.viewew_out_pipe is not None:
            #     _ = self.viewew_out_pipe.get(True)

            if self.signal_pipe is not None:
                self.signal_pipe.put(in_info)

    def stop(self):
        self.terminate()


class IR(Camera):
    def __init__(self, index, config=None):
        super(IR, self).__init__()
        self.index = index

        self.fps = 30
        self.width = 640
        self.height = 480

        if config is not None:
            self.fps = config['IR']['fps']
            self.width = config['IR']['width']
            self.height = config['IR']['height']

    def _get_cam(self):
        devs = openni2.Device.open_all()
        self.index = min(self.index, len(devs) - 1)
        self.dev = devs[self.index]

        cam = self.dev.create_ir_stream()
        cam.set_mirroring_enabled(False)
        cam.set_video_mode(
            c_api.OniVideoMode(pixelFormat=c_api.OniPixelFormat.ONI_PIXEL_FORMAT_GRAY16,
                               resolutionX=self.width,
                               resolutionY=self.height,
                               fps=self.fps))

        cam.start()
        return cam

    def _release_cam(self, cam):
        cam.stop()

    def _get_frame(self, cam):
        frame = cam.read_frame()
        frame_data = frame.get_buffer_as_uint16()
        img = np.ndarray((frame.height, frame.width), dtype=np.uint16, buffer=frame_data).astype('float')
        img = np.uint8(img / 4.0)
        return img


class RGB(Camera):
    def __init__(self, index, config=None):
        super(RGB, self).__init__()
        self.index = index

        self.fps = 30
        self.width = 970
        self.height = 720
        self.is_gray = False

        if config is not None:
            self.fps = config['RGB']['fps']
            self.width = config['RGB']['width']
            self.height = config['RGB']['height']
            self.is_gray = config['RGB'].get('is_gray', False)

    def _release_cam(self, cam):
        cam.release()
        cv2.destroyAllWindows()

    def _get_cam(self):
        cap = cv2.VideoCapture(self.index)
        time.sleep(0.1)
        cap.release()
        time.sleep(0.1)
        cap = cv2.VideoCapture(self.index)
        cap.set(6, cv2.VideoWriter.fourcc(*'MJPG'))

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FPS, self.fps)

        return cap

    def _get_frame(self, cam):
        ret, frame = cam.read()
        try:
            # print(frame.shape)
            pass
        except:
            print(self.index)
        if self.is_gray:
            frame = frame[:, :, 0]
        return frame


class FakeRGB(Camera):
    def __init__(self, index, config=None):
        super(FakeRGB, self).__init__()
        self.index = index

        self.fps = 30
        self.width = 640
        self.height = 480
        if config is not None:
            self.fps = config['RGB']['fps']
            self.width = config['RGB']['width']
            self.height = config['RGB']['height']

    def _get_cam(self):
        return 1

    def _get_frame(self, cam):
        cap = cv2.VideoCapture(self.index + cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FPS, self.fps)
        ret, frame = cap.read()
        cap.release()
        return frame


class GroupRGBs(Camera):
    def __init__(self, index_list, config=None):
        super(GroupRGBs, self).__init__()
        self.index_list = index_list

        self.fps = 30
        self.width = 640
        self.height = 480
        if config is not None:
            self.fps = config['RGB']['fps']
            self.width = config['RGB']['width']
            self.height = config['RGB']['height']

    def _get_cam(self):
        return 1

    def _get_frame(self, cam):
        frames = []
        for index in self.index_list:
            cap = cv2.VideoCapture(index + cv2.CAP_DSHOW)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            cap.set(cv2.CAP_PROP_FPS, self.fps)
            ret, frame = cap.read()
            cap.release()
            frames.append(frame)
        return frames


def get_camera(cam_type):
    if cam_type == 'IR':
        return IR
    if cam_type == 'RGB':
        return RGB
    if cam_type == 'GroupRGBs':
        return GroupRGBs
