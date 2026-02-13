import cv2
import numpy as np
from agno.agent import Agent, Toolkit
from agno.media import Image
from agno.models.google import Gemini
from PySide6.QtCore import QObject, Signal, Slot

from src.prompt import sys_prompt


class Live2dTools(Toolkit):
    """Live2D 模型控制工具集，供 Agent 调用以切换表情和播放动作。"""

    def __init__(self, agent_worker: "AgentWorker"):
        super().__init__(
            name="live2d_model_controls",
            instructions=(
                "使用这些工具来控制你的 Live2D 模型表情和动作。"
                "当你想表达某种情绪时，调用 set_expression 切换表情；"
                "当你想做出动作时，调用 start_motion 播放动作。"
            ),
            add_instructions=True,
        )
        self._agent_worker = agent_worker
        self._expression_ids: list[str] = []
        self._motion_groups: dict[str, int] = {}
        self.register(self.set_expression)
        self.register(self.start_motion)
        self.register(self.get_available_expressions)
        self.register(self.get_available_motions)

    def update_model_info(self, expression_ids: list, motion_groups: dict):
        """更新可用的表情和动作信息。"""
        self._expression_ids = expression_ids
        self._motion_groups = motion_groups

    def get_available_expressions(self) -> str:
        """获取当前模型所有可用的表情 ID 列表。"""
        if not self._expression_ids:
            return "当前没有可用的表情。"
        return "可用表情: " + ", ".join(self._expression_ids)

    def get_available_motions(self) -> str:
        """获取当前模型所有可用的动作组及每组动作数量。"""
        if not self._motion_groups:
            return "当前没有可用的动作。"
        items = [
            f"{group}（{count}个动作，index: 0~{count - 1}）"
            for group, count in self._motion_groups.items()
        ]
        return "可用动作组: " + ", ".join(items)

    def set_expression(self, expression_id: str) -> str:
        """切换 Live2D 模型的表情。

        Args:
            expression_id: 表情 ID，必须是 get_available_expressions 返回的有效 ID 之一。
        """
        if expression_id not in self._expression_ids:
            return f"无效的表情 ID: {expression_id}。可用: {', '.join(self._expression_ids)}"
        self._agent_worker.expression_requested.emit(expression_id)
        return f"已切换表情: {expression_id}"

    def start_motion(self, group: str, index: int = 0) -> str:
        """播放 Live2D 模型的动作。

        Args:
            group: 动作组名称，必须是 get_available_motions 返回的有效组名之一。
            index: 动作在组内的索引，从 0 开始。
        """
        if group not in self._motion_groups:
            return (
                f"无效的动作组: {group}。可用: {', '.join(self._motion_groups.keys())}"
            )
        max_idx = self._motion_groups[group] - 1
        if index < 0 or index > max_idx:
            return f"索引超出范围，{group} 的有效 index: 0~{max_idx}"
        self._agent_worker.motion_requested.emit(group, index)
        return f"已播放动作: {group}[{index}]"


class AgentWorker(QObject):
    """Agent 工作线程：接收文本或屏幕截图，调用 LLM 并发射响应文本。"""

    response_ready = Signal(str)
    expression_requested = Signal(str)
    motion_requested = Signal(str, int)

    def __init__(self) -> None:
        super().__init__()
        self._live2d_tools = Live2dTools(self)
        self.agent = Agent(
            model=Gemini(id="gemini-3-flash-preview"),
            system_message=sys_prompt,
            tools=[self._live2d_tools],
        )

    # ── 模型信息接收 ──

    @Slot(list, dict)
    def on_model_info(self, expression_ids: list, motion_groups: dict):
        """接收模型加载完成后的表情和动作信息。"""
        self._live2d_tools.update_model_info(expression_ids, motion_groups)
        print(
            f"[Agent] 已接收模型信息 - 表情: {len(expression_ids)} 个, 动作组: {len(motion_groups)} 个"
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
