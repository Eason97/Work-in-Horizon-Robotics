import json
import os
import time
from multiprocessing import Manager, Process, Queue

import cv2
import psutil
import zmq
from PyQt5.QtMultimedia import QCameraInfo

from .Camera import get_camera
from .Inference import Inference
from .PresetViewer import PresetViewer
from .Viewer import Viewer
from .Writer import get_writer


def _release_cameras(camera_num):
    for i in range(camera_num):
        cap = cv2.VideoCapture(i)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 30)
        _ = cap.read()
        cap.release()
        time.sleep(0.01)
        # cv2.destroyAllWindows()


def getCameraNum():
    CameraNum = 0
    for i in range(20):
        cap = cv2.VideoCapture(i)
        ret, frame = cap.read()
        _ = cap.read()
        cap.release()

        if not ret:
            break
        else:
            CameraNum = i + 1
    return CameraNum


class Controller:
    def __init__(self, Button_num, camera_num=3, dst_dir='', client_server='server', with_audio=False):

        # time_stamp = int(time.time())
        if camera_num is None:
            # 未设置摄像头数量camera_num，可自动搜素摄像头数量，但不稳定，尽量设置摄像头数量
            camera_num = getCameraNum()
        else:
            # 根据设置的摄像头数量，释放摄像头
            _release_cameras(camera_num)

        print('Found {} Cameras'.format(camera_num))
        self.client_server = client_server
        if Button_num == 0:
            self.camera_groups = Manager().dict()
            self.camera_num = len(self.camera_groups)
        else:
            self.camera_groups = {'LeftUp': 0}
            self.camera_num = camera_num
        self.dst_dir = dst_dir
        self.with_audio = with_audio
        self.work_mode = 0

        # 根据选择的摄像头数量，为每个摄像头创建进程（帧采集，帧存储，模型预测）
        self.processes = self._get_camera_processes()
        self.writers = self._get_writers()
        self.inferences = self._get_inferences()
        # 界面显示进程仅创建一个，所有摄像头共用
        self.viewer = Viewer(Button_num, client_server)

        self.process_psutil = []
        self.writer_psutil = []
        self.infer_psutil = []

        self.audio_recoder = None
        if with_audio:
            self.audio_recoder = self._get_audio_recoder()

        # 设置哥进程同步的信息队列，与系统状态信息
        self._set_pipes()
        self._set_status_dict()

    # 运行摄像头预选择界面
    def _preset_run(self, camera_groups, camera_num):
        self.preset = PresetViewer(camera_groups, camera_num)
        self.preset.start()
        self.preset.join()

    # 创建摄像头图像帧采集进程
    def _get_camera_processes(self):
        camera_processes = []

        config = {'RGB': {}}
        config['RGB']['fps'] = 25
        config['RGB']['width'] = 1270
        config['RGB']['height'] = 720
        config['RGB']['is_gray'] = False

        for i, (key, val) in enumerate(self.camera_groups.items()):
            camera_process = get_camera('RGB')(val, config)
            camera_processes.append(camera_process)

        return camera_processes

    # 创建摄像头视频存储进程
    def _get_writers(self):
        writers = []
        base_num = (3, 0)[self.client_server == 'server']

        camera_type = []
        camera_type += ['RGB_' + key for key, _ in self.camera_groups.items()]

        for i in range(len(camera_type)):
            writer = get_writer('Single')(self.dst_dir, camera_type[i])
            writers.append(writer)

        return writers

    # 创建模型预测进程
    def _get_inferences(self):
        inference_processes = []
        for i in range(self.camera_num):
            inference_process = Inference(i)
            inference_processes.append(inference_process)

        return inference_processes

    # 初始化系统各参数
    def _set_status_dict(self):
        self.status_dict = Manager().dict({
            'status': 0,
            'frame_id': 0,
            'fps': 0,
            'time_stamp': 'temp',
            'time': 0,
            'dir_info': 'temp',
            'note': 'None',
            'work_mode': 0,
            'work_mode_temp': 0,
            'is_infer': False,
            'record_fps': 0,
            'record_ratio': 1,
            'record_pixel': (1920, 1080),
            'is_restart': False
        })
        self.img_map = Manager().list([str(i) for i in range(self.camera_num)])
        self.no_show_flag = Manager().list([False] * self.camera_num)
        self.infer_mask = []
        for i in range(self.camera_num):
            sub_mask = Manager().dict({'w/o show': False, 'fatigue': False, 'smoke': False, 'emotion': False})
            self.infer_mask.append(sub_mask)

        for process in self.processes:
            process.set_status_dict(self.status_dict)
        for writer in self.writers:
            writer.set_status_dict(self.status_dict, self.img_map)
        for infer in self.inferences:
            infer.set_status_dict(self.status_dict, self.infer_mask)
        self.viewer.set_status_dict(self.status_dict, self.infer_mask, self.camera_groups, self.no_show_flag)
        if self.with_audio:
            self.audio_recoder.set_status_dict(self.status_dict)

    # 创建进程间同步的消息队列
    def _set_pipes(self):
        self.in_pipes = []
        self.single_pipes = []
        self.writer_pipes = []
        self.viewer_in_pipes = []
        self.viewer_out_pipes = []
        self.inference_in_pipes = []
        self.inference_out_pipes = []

        for process, writer, inference in zip(self.processes, self.writers, self.inferences):
            in_pipe = Queue()
            single_pipe = Queue()
            writer_pipe = Queue()
            viewew_in_pipe = Queue()
            viewew_out_pipe = Queue()
            inference_in_pipe = Queue()
            inference_out_pipe = Queue()

            self.in_pipes.append(in_pipe)
            self.single_pipes.append(single_pipe)
            self.writer_pipes.append(writer_pipe)
            self.viewer_in_pipes.append(viewew_in_pipe)
            self.viewer_out_pipes.append(viewew_out_pipe)
            self.inference_in_pipes.append(inference_in_pipe)
            self.inference_out_pipes.append(inference_out_pipe)

            process.set_pipe(in_pipe, [inference_in_pipe, viewew_in_pipe, writer_pipe], single_pipe, viewew_out_pipe)
            writer.set_pipe(writer_pipe)
            inference.set_pipe(inference_in_pipe, inference_out_pipe, writer_pipe)

        self.viewer_begin = Queue()
        self.viewer.set_pipe([self.viewer_in_pipes, self.inference_out_pipes, self.viewer_out_pipes, self.viewer_begin])

    # 停止所有进程
    def stop(self):
        for in_pipe in self.in_pipes:
            in_pipe.put(False)
        time.sleep(1)

        for process in self.processes:
            process.terminate()
        for writer in self.writers:
            writer.terminate()
        for infer in self.inferences:
            infer.terminate()
        self.viewer.terminate()
        if self.with_audio:
            self.audio_recoder.terminate()

    # 启动所有进程
    def start(self):

        for process in self.processes:
            process.start()
            pause = psutil.Process(process.pid)
            self.process_psutil.append(pause)
        for writer in self.writers:
            writer.start()
            pause = psutil.Process(writer.pid)
            self.writer_psutil.append(pause)
        for infer in self.inferences:
            infer.start()
            pause = psutil.Process(infer.pid)
            self.infer_psutil.append(pause)
            pause.suspend()

        self.viewer.start()
        if self.with_audio:
            self.audio_recoder.start()

    # 计算帧率
    def get_speed(self):
        tic_list = getattr(self, 'tic_list', [])
        tic_list.append(time.time())
        self.tic_list = tic_list
        speed = 0
        if len(tic_list) > 100:
            speed = 100 / (tic_list[-1] - tic_list[0])
            speed = '{:.2f}'.format(speed)
            tic_list.pop(0)
        elif len(tic_list) > 2:
            speed = (len(tic_list) - 1) / (tic_list[-1] - tic_list[0] + 1e-5)
            speed = '{:.2f}'.format(speed)
        return speed

    def _init_start(self):
        self.start()

    # 调试用，用于显示各进程的运行状态
    def show_process_status(self):
        camera = []
        for pause in self.process_psutil:
            camera.append(pause.status())
        infer = []
        for pause in self.infer_psutil:
            infer.append(pause.status())
        writer = []
        for pause in self.writer_psutil:
            writer.append(pause.status())
        print(' camera:', camera, ' infer:', infer, ' writer:', writer)
        # print('\r', ' camera:', camera, ' infer:', infer, ' writer:', writer, end="", flush=True)

    # 发送帧同步信号，同时判断工作模式（录制，测试）是否改变，如改变则对应调整各进程的状态
    def send_info(self):

        self.status_dict['work_mode'] = self.status_dict['work_mode_temp']
        for i in range(self.camera_num):
            self.no_show_flag[i] = self.infer_mask[i]['w/o show']

        if self.status_dict['work_mode'] == 0:  #录制
            if self.work_mode != self.status_dict['work_mode']:
                self.work_mode = 0
                for pause in self.writer_psutil:
                    if pause.status() in 'stopped':
                        pause.resume()
                for pause in self.infer_psutil:
                    if pause.status() in 'running':
                        pause.suspend()
                for pause in self.process_psutil:
                    if pause.status() in 'stopped':
                        pause.resume()
                time.sleep(0.1)

            for in_pipe in self.in_pipes:
                in_pipe.put(self.frame_index)
            self.viewer_begin.put(self.frame_index)

        elif self.status_dict['work_mode'] == 1:  #测试
            if self.work_mode != self.status_dict['work_mode']:
                self.work_mode = 1
                # print('to testing')
                # for pause in self.writer_psutil:
                #     if pause.status() in 'running':
                #         pause.suspend()
                for i in range(self.camera_num):
                    if self.no_show_flag[i]:
                        if self.process_psutil[i].status() in 'running':
                            self.process_psutil[i].suspend()
                        if self.writer_psutil[i].status() in 'running':
                            self.writer_psutil[i].suspend()
                    else:
                        self.infer_psutil[i].resume()
                time.sleep(0.1)

            for i in range(self.camera_num):
                if self.no_show_flag[i]:
                    if self.process_psutil[i].status() in 'running':
                        self.process_psutil[i].suspend()
                        if self.infer_psutil[i].status() in 'running':
                            self.infer_psutil[i].suspend()
                        if self.writer_psutil[i].status() in 'running':
                            self.writer_psutil[i].suspend()
                        time.sleep(0.1)
                else:
                    if self.process_psutil[i].status() in 'stopped':
                        self.process_psutil[i].resume()
                        self.infer_psutil[i].resume()
                        self.writer_psutil[i].resume()
                        time.sleep(0.1)

            for i in range(self.camera_num):
                if not self.no_show_flag[i]:
                    self.in_pipes[i].put(self.frame_index)
            self.viewer_begin.put(self.frame_index)

        # self.show_process_status()

    # 等待各进程完成相应操作，回传信号，结束一次帧同步
    def recv_info(self):
        for i, single_pipe in enumerate(self.single_pipes):
            if self.status_dict['work_mode'] == 1 and self.no_show_flag[i]:
                continue
            _ = single_pipe.get(True)

    # 检查控制窗口是否还存活
    def check_alive(self):
        if not self.viewer.is_alive() or self.status_dict['status'] == -100:
            self.status_dict['status'] = -100
            self.stop()
            return False
        return True

    # 系统帧同步循环，并在循环过程中检查运行状态
    def run(self):

        self.frame_index = -1
        self._init_start()

        while True:
            if self.status_dict['status'] == 2:
                self.status_dict['status'] = 1
                self.status_dict['time_stamp'] = str(int(time.time()))
                print('dst dir has changed')
                self.frame_index = -1

            self.frame_index += 1

            self.send_info()
            self.recv_info()

            self.status_dict['frame_id'] = self.frame_index
            self.status_dict['fps'] = self.get_speed()
            if self.status_dict['time_stamp'] != 'temp':
                self.status_dict['time'] = int(time.time()) - int(self.status_dict['time_stamp'])

            if self.check_alive() is False:
                # _release_cameras(self.camera_num)
                break


class remoteController(Controller):
    def __init__(self, camera_num=5, dst_dir='', tcp='tcp://*:6010', client_server='server', client_num=2, client_id=0):
        super(remoteController, self).__init__(camera_num, dst_dir, client_server)
        self.tcp = tcp
        self.client_server = client_server
        self.client_id = client_id
        self.client_num = client_num

    def _get_socket(self):
        tcp_id = int(self.tcp.split(':')[-1])

        if self.client_server == 'server':
            socket = []
            for i in range(self.client_num):
                context = zmq.Context()
                temp_socket = context.socket(zmq.REP)
                tcp = self.tcp.replace(':' + str(tcp_id), ':' + str(tcp_id + i))
                print(tcp)
                temp_socket.bind(tcp)
                socket.append(temp_socket)

        elif self.client_server == 'client':
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            tcp = self.tcp.replace(':' + str(tcp_id), ':' + str(tcp_id + self.client_id))
            socket.connect(tcp)
        else:
            raise Exception("{} is not in ['server','clinet']".format(self.client_server))

        return socket

    def _init_start(self):
        self.start()

        self.socket = self._get_socket()
        self.int_encoder = lambda x: str(x).encode('utf-8')
        self.dict_encoder = lambda x: json.dumps(x).encode('utf-8')
        self.dict_decoder = lambda x: json.loads(x.decode('utf-8'))

        if self.client_server == 'server':
            for i in range(self.client_num):
                _ = self.socket[i].recv()
        elif self.client_server == 'client':
            self.socket.send(self.int_encoder(self.client_id))

    def send_info(self):

        if self.client_server == 'server':
            socket_info = {
                'frame_index': self.frame_index,
                'status': self.status_dict['status'],
                'time_stamp': self.status_dict['time_stamp'],
                'dir_info': self.status_dict['dir_info'],
                'note': self.status_dict['note']
            }
            for i in range(self.client_num):
                self.socket[i].send(self.dict_encoder(socket_info))

        elif self.client_server == 'client':
            socket_info = self.socket.recv()
            socket_info = self.dict_decoder(socket_info)
            self.frame_index = socket_info['frame_index']
            self.status_dict['status'] = socket_info['status']
            self.status_dict['time_stamp'] = socket_info['time_stamp']
            self.status_dict['dir_info'] = socket_info['dir_info']
            self.status_dict['note'] = socket_info['note']

        for in_pipe in self.in_pipes:
            in_pipe.put(self.frame_index)

    def recv_info(self):
        for single_pipe in self.single_pipes:
            _ = single_pipe.get(True)

        if self.client_server == 'server':
            for i in range(self.client_num):
                _ = self.socket[i].recv()

        elif self.client_server == 'client':
            self.socket.send(self.int_encoder(self.client_id))

    def check_alive(self):
        if not self.viewer.is_alive() or self.status_dict['status'] == -100:
            self.status_dict['status'] = -100

            if self.client_server == 'server':
                socket_info = {
                    'frame_index': self.frame_index,
                    'status': self.status_dict['status'],
                    'time_stamp': self.status_dict['time_stamp']
                }
                self.socket.send(self.dict_encoder(socket_info))
                time.sleep(0.001)

            self.stop()
            return False
        return True
