"""输入控制器：当 Agent 正在处理时，丢弃新的输入请求。"""

import numpy as np
from PySide6.QtCore import QObject, Signal, Slot


class Controller(QObject):
    """
    位于输入源（屏幕变化 / ASR 文本）和 AgentWorker 之间，
    确保同一时间只有一个请求被处理，Agent 忙碌时丢弃后续输入。
    """

    # 转发给 AgentWorker 的信号
    text_accepted = Signal(str)
    screen_accepted = Signal(float, np.ndarray)

    def __init__(self) -> None:
        super().__init__()
        self._busy = False

    @property
    def is_busy(self) -> bool:
        return self._busy

    # ── 输入槽 ──

    @Slot(str)
    def on_text_input(self, text: str):
        """接收 ASR 转写文本；Agent 空闲时转发，忙碌时丢弃。"""
        if self._busy:
            print("[Controller] Agent 忙碌中，丢弃文本输入")
            return
        self._busy = True
        print("[Controller] 转发文本输入给 Agent")
        self.text_accepted.emit(text)

    @Slot(float, np.ndarray)
    def on_screen_change(self, score: float, img: np.ndarray):
        """接收屏幕变化；Agent 空闲时转发，忙碌时丢弃。"""
        if self._busy:
            print("[Controller] Agent 忙碌中，丢弃屏幕输入")
            return
        self._busy = True
        print(f"[Controller] 转发屏幕变化 (score={score:.2f}) 给 Agent")
        self.screen_accepted.emit(score, img)

    # ── Agent 完成后的回调 ──

    @Slot(str)
    def on_agent_done(self, _text: str):
        """Agent 返回响应后，解除忙碌状态，允许接受新输入。"""
        self._busy = False
        print("[Controller] Agent 处理完毕，恢复接受输入")
