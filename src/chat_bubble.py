"""粉色对话气泡窗口，用于显示 Agent 的回复文本。"""

from PySide6.QtCore import QPropertyAnimation, Qt, QTimer, Slot
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath
from PySide6.QtWidgets import QLabel, QWidget


class ChatBubble(QWidget):
    """无边框粉色圆角对话气泡，自动跟随父窗口定位并在若干秒后淡出。"""

    # 样式常量
    BG_COLOR = QColor(255, 182, 193, 230)  # 粉色半透明
    TEXT_COLOR = QColor(80, 20, 40)
    BORDER_COLOR = QColor(255, 130, 160, 200)
    RADIUS = 18
    PADDING = 16
    MAX_WIDTH = 360
    DISPLAY_SECONDS = 8
    TAIL_SIZE = 12  # 小尾巴大小

    def __init__(self, parent_widget: QWidget | None = None):
        # 使用独立顶层窗口，这样即使父控件是 OpenGL 也不会出问题
        super().__init__(None)
        self._parent_widget = parent_widget

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        # 文本标签
        self._label = QLabel(self)
        self._label.setWordWrap(True)
        self._label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._label.setFont(QFont("Microsoft YaHei", 11))
        self._label.setStyleSheet(
            f"color: {self.TEXT_COLOR.name()}; background: transparent;"
        )
        self._label.setMaximumWidth(self.MAX_WIDTH - 2 * self.PADDING)

        # 自动隐藏定时器
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._fade_out)

        # 淡出动画
        self._fade_anim: QPropertyAnimation | None = None

        self.hide()

    # ── 公共接口 ──

    @Slot(str)
    def show_message(self, text: str):
        """显示一条新消息，自动定位与定时隐藏。"""
        self._hide_timer.stop()
        if (
            self._fade_anim
            and self._fade_anim.state() == QPropertyAnimation.State.Running
        ):
            self._fade_anim.stop()
        self.setWindowOpacity(1.0)

        self._label.setText(text)
        self._label.adjustSize()

        # 计算气泡尺寸
        lw = self._label.width()
        lh = self._label.height()
        bubble_w = lw + 2 * self.PADDING
        bubble_h = lh + 2 * self.PADDING + self.TAIL_SIZE
        self.setFixedSize(bubble_w, bubble_h)
        self._label.move(self.PADDING, self.PADDING)

        # 定位：在父窗口的左上方弹出
        self._reposition()

        self.show()
        self.raise_()
        self._hide_timer.start(self.DISPLAY_SECONDS * 1000)

    # ── 绘制 ──

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        body_h = h - self.TAIL_SIZE

        # 圆角矩形主体
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, body_h, self.RADIUS, self.RADIUS)

        # 小尾巴（底部右侧三角）
        tail_x = w - 50
        tail = QPainterPath()
        tail.moveTo(tail_x, body_h)
        tail.lineTo(tail_x + self.TAIL_SIZE, h)
        tail.lineTo(tail_x + 2 * self.TAIL_SIZE, body_h)
        tail.closeSubpath()
        path = path.united(tail)

        painter.setPen(self.BORDER_COLOR)
        painter.setBrush(self.BG_COLOR)
        painter.drawPath(path)
        painter.end()

    # ── 内部方法 ──

    def _reposition(self):
        """将气泡定位到父窗口的左上角偏移处。"""
        if self._parent_widget is None:
            return
        parent_pos = self._parent_widget.pos()
        # 显示在模型窗口左上角上方
        x = parent_pos.x() + 20
        y = parent_pos.y() - self.height() + 30
        # 确保不超出屏幕顶部
        if y < 0:
            y = parent_pos.y() + 20
        self.move(x, y)

    def _fade_out(self):
        """淡出动画后隐藏。"""
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(600)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self.hide)
        self._fade_anim.start()
