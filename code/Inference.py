import random
import sys
from multiprocessing import Process

import cv2


class Inference(Process):

    infer_curve = dict({
        'fatigue': ['Fdata0', 'Fdata1', 'Fdata2'],
        'emotion': ['Edata0', 'Edata1'],
        'smoke': ['Sdata0', 'Sdata1']
    })

    def __init__(self, index):
        Process.__init__(self)
        self.in_pipe = None
        self.out_pipe = None
        self.status_dict = None
        self.infer_mask = None
        self.writer_pipe = None
        self.index = index

    def set_pipe(self, in_pipe=None, out_pipe=None, writer_pipe=None):
        self.in_pipe = in_pipe
        self.out_pipe = out_pipe
        self.writer_pipe = writer_pipe

    def set_status_dict(self, status_dict=None, infer_mask=None):
        self.status_dict = status_dict
        self.infer_mask = infer_mask

    def fatigue_model(self, in_img):
        output_type = ['low', 'mid', 'high']

        # if dis_img is None or in_img is None:
        #     print(dis_img.shape, in_img.shape)
        #     return None, None
        #
        # dis_text = output_type[random.randint(0, 2)]
        # cv2.putText(dis_img, dis_text, (0, 100), cv2.FONT_HERSHEY_COMPLEX, 5.0, (100, 200, 200), 8)

        curve_data = dict()
        for data_type in self.infer_curve['fatigue']:
            curve_data[data_type] = int(random.randint(0, 100))

        return curve_data

    # def fatigue_model(self, in_img):
    #     if in_img is None:
    #         print('in_img is none')
    #         return None
    #
    #     data = fatigue_test(in_img)
    #
    #     return data

    def emotion_model(self, in_img=None):
        output_type = ['E0', 'E1']

        # if dis_img is None or in_img is None:
        #     return None, None
        #
        # dis_text = output_type[random.randint(0, 1)]
        # cv2.putText(dis_img, dis_text, (500, 100), cv2.FONT_HERSHEY_COMPLEX, 5.0, (100, 200, 200), 8)

        curve_data = dict()
        for data_type in self.infer_curve['emotion']:
            curve_data[data_type] = random.randint(0, 100)

        return curve_data

    def smoke_model(self, in_img=None):
        output_type = ['S0', 'S1']

        # if in_img is None:
        #     return None, None
        #
        # dis_text = output_type[random.randint(0, 1)]
        # cv2.putText(dis_img, dis_text, (0, 500), cv2.FONT_HERSHEY_COMPLEX, 5.0, (100, 200, 200), 8)

        curve_data = dict()
        for data_type in self.infer_curve['smoke']:
            curve_data[data_type] = random.randint(0, 100)

        return curve_data

    def run(self):
        while True:
            if self.in_pipe is not None:
                break

        while True:
            input = self.in_pipe.get(True)
            if input is False:
                break
            in_info, input_img = input
            display_img = input_img
            curve_data = dict()
            if self.status_dict['is_infer'] and self.status_dict['work_mode'] == 1:
                if self.infer_mask[self.index]['fatigue']:
                    sub_curve_data = self.fatigue_model(input_img)
                    curve_data.update(sub_curve_data)
                if self.infer_mask[self.index]['smoke']:
                    sub_curve_data = self.smoke_model(input_img)
                    curve_data.update(sub_curve_data)
                if self.infer_mask[self.index]['emotion']:
                    sub_curve_data = self.emotion_model(input_img)
                    curve_data.update(sub_curve_data)

            # print(self.index, 'infer:', output)

            if self.out_pipe is not None:
                self.out_pipe.put([in_info, [display_img, curve_data]])
            if self.writer_pipe is not None:
                self.writer_pipe.put([in_info, [display_img, curve_data]])

    def stop(self):
        self.terminate()
