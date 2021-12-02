import json
import os
import random
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Process
from subprocess import PIPE, Popen

import cv2
from cv2 import VideoWriter, VideoWriter_fourcc, imread, resize
from PIL import Image


class BigWriter:
    def __init__(self, video_src, fps=None):
        self.video_path = '.'.join(video_src.split('.')[:-1])
        if not os.path.exists(self.video_path):
            os.makedirs(self.video_path)
        self.status = True
        self.frame_id = -1
        self.threads = []
        # self.executor = ThreadPoolExecutor(max_workers=10)

    def write(self, img):
        self.frame_id += 1
        img_path = os.path.join(self.video_path, '{}.jpg'.format(str(self.frame_id).zfill(10)))
        # self.executor.submit(cv2.imwrite,(img_path,img,))
        # plt.imsave(img_path,img)
        cv2.imwrite(img_path, img)
        # th = threading.Thread(target=cv2.imwrite,args=(img_path,img,))
        # th.start()
        # self.threads.append(th)
        # if len(self.threads) > 20:
        #     th = self.threads.pop(0)
        #     th.join()

    def release(self):
        self.status = False

    def isOpened(self):
        return self.status


class PILWriter:
    def __init__(self, video_src, fps):
        self.status = True

        self.p = Popen([
            'ffmpeg', '-y', '-f', 'image2pipe', '-vcodec', 'mjpeg', '-r',
            str(fps), '-i', '-', '-vcodec', 'mpeg4', '-qscale', '5', '-r',
            str(fps), video_src
        ],
                       stdin=PIPE)

    def write(self, img):
        img = Image.fromarray(img)
        img.save(self.p.stdin, 'JPEG')

    def release(self):
        self.p.stdin.close()
        self.p.wait()
        self.status = False

    def isOpened(self):
        return self.status


class Writer(Process):
    def __init__(self, root_dir, camera_name):
        Process.__init__(self)

        self.dst_dir = None
        self.in_pipe = None
        self.status_dict = None
        self.root_dir = root_dir
        self.camera_name = camera_name

    def set_pipe(self, in_pipe=None):
        self.in_pipe = in_pipe

    def set_status_dict(self, status_dict=None, img_map=None):
        self.status_dict = status_dict
        self.img_map = img_map

    def save_input(self, input):
        pass

    def check_dir(self, dst_dir):
        try:
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir)
        except:
            pass

    def _dir_info2dirs(self, dir_info):
        dir_info = dir_info.split('||')
        dir_info = [v.strip() for v in dir_info]
        return dir_info

    def run(self):
        while True:
            if self.in_pipe is not None:
                break

        time_stamp = 'temp'
        dir_info = '/'

        fps = 30
        video_shape = (1280, 720)

        videoWriter = None
        status = 0

        sec_fps = 0
        ignore_fps = 0

        while True:
            input = self.in_pipe.get(True)

            if input is False and videoWriter is not None:
                if videoWriter.isOpened():
                    videoWriter.release()
                break

            in_info, data = input
            in_info, tic = in_info

            if isinstance(data, list):
                img, curve_data = data
            else:
                img = data
                curve_data = ''

            if self.status_dict['status'] == 1:
                temp_time_stamp = self.status_dict.get('time_stamp', 'temp')
                if temp_time_stamp != time_stamp:
                    time_stamp = temp_time_stamp

                    video_name = '{}.avi'.format(self.camera_name)
                    dir_info = self.status_dict.get('dir_info', 'temp')
                    time_local = time.localtime(int(time_stamp))
                    file_time = time.strftime("%Y-%m-%d_%H-%M-%S", time_local)
                    dst_dir = os.path.join(dir_info, file_time)
                    # print(dst_dir)
                    self.check_dir(dst_dir)
                    video_src = os.path.join(dst_dir, video_name)

                    # print(video_src)
                    txt_scr = video_src.replace('.avi', '.txt')
                    # json_scr = video_src.replace('.avi', '.json')

                    # videoWriter = PILWriter(video_src, fps)

                    fourcc = VideoWriter_fourcc(*"XVID")
                    set_fps = self.status_dict.get('record_fps', 0)
                    max_fps = int(float(self.status_dict.get('fps', 30)))
                    if set_fps == 0 or set_fps > max_fps:
                        fps = max_fps
                    elif set_fps < max_fps:
                        if sec_fps == 0:
                            sec_fps = max_fps
                            ignore_fps = max_fps - set_fps
                        sec_fps -= 1
                        if ignore_fps and random.choice([True, False]):
                            ignore_fps -= 1
                            continue

                    video_shape = self.status_dict.get('record_pixel', (1280, 720))
                    videoWriter = cv2.VideoWriter(video_src, fourcc, fps, video_shape)
                    # fps = self.status_dict.get('record_fps', 30)
                    # container = av.open(video_src, mode='w')
                    # stream = container.add_stream('mpeg4', rate=fps)
                    # stream.width = video_shape[0]
                    # stream.height = video_shape[1]
                    # stream.pix_fmt = 'yuv420p'
                    status = 1

                if 'IR' in self.camera_name:
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

                img = cv2.resize(img, video_shape)
                videoWriter.write(img)

                with open(txt_scr, 'a') as f:
                    img_name = '{}_{} {}\n'.format(str(in_info).zfill(6), tic, str(curve_data))
                    f.write(img_name)
                # with open(json_scr, "w") as f:
                #     json.dump(curve_data, f)

            elif self.status_dict['status'] == 0 and status == 1:
                status = 0
                videoWriter.release()
                # for packet in stream.encode():
                #     container.mux(packet)
                # container.close()

                if self.status_dict['note'] != 'None':
                    with open(txt_scr, 'a') as f:
                        f.write(self.status_dict['note'])
                        f.close()
                # with open(json_scr, "w") as f:
                #     f.close()

                new_dir_info = self.status_dict.get('dir_info', 'temp')
                if new_dir_info != dir_info:
                    # self.check_dir(new_dir_info)
                    # new_dst_dir = os.path.join(new_dir_info, file_time)
                    self.check_dir(new_dir_info)
                    try:
                        new_dir = os.path.join(new_dir_info, file_time)
                        if not os.path.exists(new_dir):
                            shutil.move(dst_dir, new_dir_info)
                    except:
                        pass

    def stop(self):
        self.terminate()


class SingleWriter(Writer):
    def __init__(self, root_dir, camera_name):
        super(SingleWriter, self).__init__(root_dir, camera_name)

    def save_input(self, input, dst_dir):
        in_info, img = input
        in_info, tic = in_info
        img_name = '{}_{}.jpg'.format(str(in_info).zfill(6), tic)

        img_path = os.path.join(dst_dir, img_name)
        th = threading.Thread(target=cv2.imwrite, args=(
            img_path,
            img,
        ))
        th.start()


class GroupsWriter(Writer):
    def __init__(self):
        super(GroupsWriter, self).__init__()

    def save_input(self, input):
        in_info, imgs = input
        in_info, tic = in_info
        for dst_dir, img in zip(self.dst_dir, imgs):
            img_name = '{}_{}.jpg'.format(str(in_info).zfill(6), tic)
            img_path = os.path.join(dst_dir, img_name)
            cv2.imwrite(img_path, img)


def get_writer(write_type):
    if write_type == 'Single':
        return SingleWriter
    if write_type == 'Group':
        return GroupsWriter
