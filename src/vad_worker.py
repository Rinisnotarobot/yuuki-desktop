import numpy as np
import sounddevice as sd
import torch
from PySide6.QtCore import QObject, QThread, Signal, Slot
from silero_vad import VADIterator, load_silero_vad


class FullSentenceWorker(QObject):
    sentence_ready = Signal(np.ndarray)
    finished = Signal()

    def __init__(self, sample_rate=16000):
        super().__init__()
        self.sample_rate = sample_rate
        self._is_active = False
        self.buffer = []  # 用于存放当前话语的音频块

        # 初始化 VAD 迭代器
        # min_silence_duration_ms: 停顿超过 300ms 则认为话讲完了
        vad_model = load_silero_vad()
        self.vad_iterator = VADIterator(
            vad_model,
            threshold=0.5,
            sampling_rate=sample_rate,
            min_silence_duration_ms=300,
        )

    @Slot()
    def start_listening(self):
        self._is_active = True
        frame_size = 512  # 16kHz 下 silero VAD 要求的帧大小

        def callback(indata, frames, time, status):
            if not self._is_active:
                raise sd.CallbackStop

            audio_data = indata.flatten()
            audio_float32 = audio_data.astype(np.float32) / 32768.0

            # 使用 VADIterator 处理帧
            # 它会返回一个字典，包含 'start' 或 'end' 键（代表采样点位置）
            speech_dict = self.vad_iterator(
                torch.from_numpy(audio_float32), return_seconds=False
            )

            if speech_dict:
                if "start" in speech_dict:
                    # 检测到开始说话，清理缓冲区并开始记录
                    self.buffer = [audio_data]
                    print("--- 检测到语音开始 ---")

                if "end" in speech_dict:
                    # 检测到结束说话，合并缓冲区发送给主线程
                    if self.buffer:
                        full_sentence = np.concatenate(self.buffer)
                        self.sentence_ready.emit(full_sentence)
                        self.buffer = []
                    print("--- 检测到语音结束 ---")
                    self.vad_iterator.reset_states()  # 重置状态准备下一句

            # 如果当前正在录制状态（缓冲区不为空），则持续添加
            elif self.buffer:
                self.buffer.append(audio_data)

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=frame_size,
            callback=callback,
        ):
            while self._is_active:
                QThread.msleep(50)

        self.finished.emit()

    @Slot()
    def stop_listening(self):
        self._is_active = False
