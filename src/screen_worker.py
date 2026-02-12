import time

import cv2
import mss
import numpy as np
from PySide6.QtCore import QObject, QThread, Signal, Slot


class ScreenChangeDetector(QObject):
    significant_change_detected = Signal(float, np.ndarray)
    finished = Signal()

    def __init__(self):
        super().__init__()
        self._is_active = False
        self.sct = None
        self.monitor_idx = 1

        # --- 参数调优 ---
        self.check_interval = 1 / 60  # 每秒60帧
        self.resize_width = 1280  # 压缩宽度，越小越忽略细节
        self.resize_height = 720  # 压缩高度
        self.threshold = 50  # 触发阈值：平均像素差异超过此值才算变化

        self.last_frame = None
        self.last_trigger_time = 0

    def get_processed_frame(self):
        """获取并预处理屏幕图像"""
        if self.sct is None:
            raise RuntimeError("mss has not been initialized")
        screenshot = self.sct.grab(self.sct.monitors[self.monitor_idx])
        img = np.array(screenshot)
        gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
        small = cv2.resize(
            gray,
            (self.resize_width, self.resize_height),
            interpolation=cv2.INTER_AREA,
        )
        blurred = cv2.GaussianBlur(small, (5, 5), 0)
        return img, blurred

    @Slot()
    def start_detecting(self):
        self._is_active = True
        self.sct = mss.mss()

        # 初始化第一帧
        _, self.last_frame = self.get_processed_frame()

        while self._is_active:
            QThread.msleep(int(self.check_interval * 1000))

            # # 冷却期检查
            # if time.time() - self.last_trigger_time < self.cooldown:
            #     continue
            original_img, current_frame = self.get_processed_frame()
            diff = cv2.absdiff(self.last_frame, current_frame)
            score = np.mean(diff)

            # print(f"当前屏幕变化率: {score:.2f}")  # 调试用

            if score > self.threshold:
                print(f"检测到显著变化！Score: {score:.2f}")
                self.last_trigger_time = time.time()
                self.significant_change_detected.emit(score, original_img)
                self.last_frame = current_frame
            else:
                self.last_frame = current_frame

        if self.sct is not None:
            self.sct.close()
            self.sct = None

        self.finished.emit()

    @Slot()
    def stop_detecting(self):
        self._is_active = False
