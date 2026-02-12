import numpy as np
import torch
from PySide6.QtCore import QObject, Signal, Slot
from transformers import AutoModel, AutoProcessor


class TranscribeWorker(QObject):
    """接收 VAD 检测到的完整语句音频，使用 GLM-ASR 进行语音识别"""

    transcription_ready = Signal(str)  # 识别完成后发出文本

    def __init__(self, sample_rate=16000):
        super().__init__()
        self.sample_rate = sample_rate
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        repo_id = "zai-org/GLM-ASR-Nano-2512"
        self.processor = AutoProcessor.from_pretrained(repo_id)
        self.model = AutoModel.from_pretrained(
            repo_id, dtype=torch.bfloat16, device_map=self.device
        )

    @Slot(np.ndarray)
    def on_sentence_audio(self, audio_data: np.ndarray):
        """接收 int16 音频数据并进行语音识别"""
        try:
            # int16 -> float32 归一化
            audio_float = audio_data.astype(np.float32) / 32768.0

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "audio",
                            "audio": audio_float,
                            "sampling_rate": self.sample_rate,
                        },
                        {
                            "type": "text",
                            "text": "Please transcribe this audio into text",
                        },
                    ],
                }
            ]

            inputs = self.processor.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_dict=True,
                return_tensors="pt",
            )
            inputs = inputs.to(self.device, dtype=torch.bfloat16)

            outputs = self.model.generate(**inputs, max_new_tokens=128, do_sample=False)
            text = self.processor.batch_decode(
                outputs[:, inputs.input_ids.shape[1] :], skip_special_tokens=True
            )[0].strip()

            if text:
                print(f"[ASR] {text}")
                self.transcription_ready.emit(text)

        except Exception as e:
            print(f"[ASR Error] {e}")
