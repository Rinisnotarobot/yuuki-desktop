import argparse
import json
import os
import traceback

import live2d.v3 as live2d
from dotenv import load_dotenv
from OpenGL.GL import glViewport
from PySide6.QtCore import QPoint, Qt, QThread, QTimerEvent, Signal, Slot
from PySide6.QtGui import QGuiApplication, QMouseEvent, QSurfaceFormat
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QApplication, QMenu

from src.agent import AgentWorker
from src.chat_bubble import ChatBubble
from src.controller import Controller
from src.screen_worker import ScreenChangeDetector
from src.transcribe_worker import TranscribeWorker
from src.vad_worker import FullSentenceWorker


class Live2DWidget(QOpenGLWidget):
    # 模型加载完成后发射，携带 expression_ids(list) 和 motion_groups(dict)
    model_info_ready = Signal(list, dict)

    def __init__(self, model_path, init_expressions=None):
        super().__init__()
        self.model_path = model_path
        self.model: live2d.LAppModel | None = None
        self.init_expressions = init_expressions or ["水印关闭.exp3.json"]

        # 无边框 + 置顶 + 透明背景 + 工具窗口（不在任务栏显示）
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # 开启鼠标追踪，使得不按键也能触发 mouseMoveEvent
        self.setMouseTracking(True)

        self.resize(1280, 720)

        # 拖拽相关
        self._dragging = False
        self._drag_offset = QPoint()

        # 对话气泡（外部赋值）
        self.chat_bubble: ChatBubble | None = None

        # 系统缩放倍率
        self._system_scale = 1

    def initializeGL(self):
        try:
            self._system_scale = QGuiApplication.primaryScreen().devicePixelRatio()

            # 1. 初始化 OpenGL 上下文
            live2d.glInit()
            # 2. 创建并加载模型
            self.model = live2d.LAppModel()
            self.model.LoadModelJson(self.model_path)
            # 3. 设置初始视口大小
            self.model.Resize(self.width(), self.height())

            # 自动加载初始表情（如水印关闭）
            self._apply_initial_expressions()

            # 发射模型可用表情 & 动作给 Agent
            expr_ids = self.model.GetExpressionIds()
            motion_groups = self.model.GetMotionGroups()
            self.model_info_ready.emit(expr_ids, motion_groups)

            # 30fps 定时器 (降低刷新率以减少资源占用和可能的闪烁)
            self.startTimer(int(1000 / 60))

        except Exception:
            traceback.print_exc()

    def resizeGL(self, w: int, h: int) -> None:
        glViewport(0, 0, w, h)
        self.model.Resize(w, h)  # type: ignore

    def paintGL(self):
        try:
            live2d.clearBuffer(0.0, 0.0, 0.0, 0.0)

            if self.model:
                self.model.Update()
                self.model.Draw()
        except Exception:
            traceback.print_exc()

    def timerEvent(self, a0: QTimerEvent | None) -> None:
        self.update()

    # ── 鼠标拖拽移动窗口 ──

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_offset = event.globalPosition().toPoint() - self.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
        else:
            x, y = (
                event.globalPosition().x() - self.x(),
                event.globalPosition().y() - self.y(),
            )
            # 缩小鼠标跟踪幅度（0.1倍），避免视线移动过大
            cx, cy = self.width() / 2, self.height() / 2
            x = cx + (x - cx) * 0.3
            y = cy + (y - cy) * 0.3

            self.model.Drag(x, y)  # type: ignore

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
        super().mouseReleaseEvent(event)

    # ── 右键菜单 ──

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        quit_action = menu.addAction("退出")
        action = menu.exec(event.globalPos())
        if action == quit_action:
            QApplication.quit()

    # ── Agent 触发的模型控制槽 ──

    @Slot(str)
    def on_set_expression(self, expression_id: str):
        """Agent 请求切换表情。"""
        if self.model:
            self.model.SetExpression(expression_id)
            print(f"[Live2D] 切换表情: {expression_id}")

    @Slot(str, int)
    def on_start_motion(self, group: str, index: int):
        """Agent 请求播放动作。"""
        if self.model:
            self.model.StartMotion(group, index, 3)  # priority=3 (Force)
            print(f"[Live2D] 播放动作: {group}[{index}]")

    @Slot()
    def on_bubble_dismissed(self):
        """对话气泡消失后，重置表情到默认状态。"""
        if self.model:
            self.model.ResetExpressions()
            print("[Live2D] 气泡消失，表情已重置")

    def on_significant_screen_change(self, score, _img):
        print(f"屏幕显著变化: {score:.2f}")

    def on_agent_response(self, text):
        """收到 Agent 回复时，通过对话气泡显示。"""
        if self.chat_bubble is not None:
            self.chat_bubble.show_message(text)

    def _apply_initial_expressions(self):
        """加载模型目录下的指定表情文件，自动应用参数"""
        if not self.model:
            print("[警告] 模型未初始化，无法应用表情")
            return

        model_dir = os.path.dirname(self.model_path)

        for exp_name in self.init_expressions:
            exp_path = os.path.join(model_dir, exp_name)
            if not os.path.exists(exp_path):
                continue
            try:
                with open(exp_path, "r", encoding="utf-8") as f:
                    exp_data = json.load(f)
                for param in exp_data.get("Parameters", []):
                    pid = param["Id"]
                    value = float(param["Value"])
                    blend = param.get("Blend", "Add")
                    if blend == "Add":
                        self.model.AddParameterValue(pid, value)
                    else:
                        self.model.SetParameterValue(pid, value)
                print(f"[表情] 已应用: {exp_name}")
            except Exception as e:
                print(f"[表情] 加载失败 {exp_name}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Yuuki Desktop")
    parser.add_argument(
        "--model",
        default="resources/狐狸学姐/狐狸学姐.model3.json",
        help="模型文件路径",
    )
    parser.add_argument(
        "--expressions",
        nargs="*",
        default=["水印关闭.exp3.json"],
        help="启动时自动应用的表情文件列表",
    )
    args, remaining = parser.parse_known_args()
    load_dotenv()

    live2d.init()

    # 设置 OpenGL 格式以支持透明
    fmt = QSurfaceFormat()
    fmt.setAlphaBufferSize(8)
    fmt.setSamples(4)
    QSurfaceFormat.setDefaultFormat(fmt)

    app = QApplication(remaining)
    widget = Live2DWidget(args.model, init_expressions=args.expressions)

    # 创建粉色对话气泡
    chat_bubble = ChatBubble(parent_widget=widget)
    chat_bubble.dismissed.connect(widget.on_bubble_dismissed)
    widget.chat_bubble = chat_bubble

    # 输入控制器（主线程，Agent 忙碌时丢弃新输入）
    controller = Controller()

    # 启动 Agent 线程
    agent_thread = QThread()
    agent_worker = AgentWorker()
    agent_worker.moveToThread(agent_thread)
    # Controller -> AgentWorker（转发被接受的输入）
    controller.text_accepted.connect(agent_worker.on_text_input)
    controller.screen_accepted.connect(agent_worker.on_screen_change)
    # AgentWorker -> 对话气泡 + Controller（解除忙碌）
    agent_worker.response_ready.connect(widget.on_agent_response)
    agent_worker.response_ready.connect(controller.on_agent_done)
    # Widget 模型加载完成 -> AgentWorker 接收表情/动作信息
    widget.model_info_ready.connect(agent_worker.on_model_info)
    # AgentWorker 工具调用 -> Widget 执行表情/动作
    agent_worker.expression_requested.connect(widget.on_set_expression)
    agent_worker.motion_requested.connect(widget.on_start_motion)
    agent_thread.start()

    screen_thread = QThread()
    detector = ScreenChangeDetector()
    detector.moveToThread(screen_thread)
    screen_thread.started.connect(detector.start_detecting)
    detector.significant_change_detected.connect(widget.on_significant_screen_change)
    # 屏幕变化 -> Controller 过滤
    detector.significant_change_detected.connect(controller.on_screen_change)
    detector.finished.connect(screen_thread.quit)
    app.aboutToQuit.connect(detector.stop_detecting)
    screen_thread.start()

    # 启动 VAD 语音监听
    vad_thread = QThread()
    vad_worker = FullSentenceWorker()
    vad_worker.moveToThread(vad_thread)
    vad_thread.started.connect(vad_worker.start_listening)
    vad_worker.finished.connect(vad_thread.quit)
    app.aboutToQuit.connect(vad_worker.stop_listening)
    vad_thread.start()

    # 启动 ASR 语音识别
    asr_thread = QThread()
    asr_worker = TranscribeWorker()
    asr_worker.moveToThread(asr_thread)
    vad_worker.sentence_ready.connect(asr_worker.on_sentence_audio)
    # ASR 转写文本 -> Controller 过滤
    asr_worker.transcription_ready.connect(controller.on_text_input)
    asr_thread.start()

    widget.show()
    app.exec()

    live2d.dispose()
