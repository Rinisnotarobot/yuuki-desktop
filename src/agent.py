import cv2
import numpy as np
from agno.agent import Agent
from agno.media import Image
from agno.models.google import Gemini
from PySide6.QtCore import QObject, Signal, Slot

from src.prompt import sys_prompt


class AgentWorker(QObject):
    """Agent 工作线程：接收文本或屏幕截图，调用 LLM 并发射响应文本。"""

    response_ready = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.agent = Agent(
            model=Gemini(id="gemini-3-flash-preview"),
            system_message=sys_prompt,
        )

    # ── 槽函数 ──

    @Slot(str)
    def on_text_input(self, text: str):
        """接收语音转文字后的文本，发送给 Agent 获取回复。"""
        if not text.strip():
            return
        try:
            print(f"[Agent] 收到文本输入: {text}")
            response = self.agent.run(text)
            reply = response.content if response.content else ""
            if reply:
                print(f"[Agent] 回复: {reply}")
                self.response_ready.emit(reply)
        except Exception as e:
            print(f"[Agent Error] {e}")

    @Slot(float, np.ndarray)
    def on_screen_change(self, score: float, img: np.ndarray):
        """接收屏幕截图（BGRA ndarray），编码为 PNG 发给 Agent 进行图像理解。"""
        try:
            # BGRA -> BGR -> PNG bytes
            bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            success, buf = cv2.imencode(".png", bgr)
            if not success:
                return
            png_bytes = buf.tobytes()

            print(f"[Agent] 收到屏幕变化 (score={score:.2f})，发送截图给 Agent...")
            response = self.agent.run(
                "主人的屏幕刚刚发生了变化，请根据屏幕内容做出你的反应。",
                images=[Image(content=png_bytes, mime_type="image/png")],
            )
            reply = response.content if response.content else ""
            if reply:
                print(f"[Agent] 回复: {reply}")
                self.response_ready.emit(reply)
        except Exception as e:
            print(f"[Agent Error] {e}")
